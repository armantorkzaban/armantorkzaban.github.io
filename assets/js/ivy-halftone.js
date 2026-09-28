/**
 * English Ivy (Hedera helix) Halftone Botanical Finial
 * Procedural stippling engine with botanical realism.
 * - Non-intrusive ambient background layer
 * - 100% full uncropped framing with safe padding
 * - Smooth continuous harmonic wave animation (motion: ON)
 * - Passive rendering: no mouseover glow or thermal flares
 * - IntersectionObserver: pauses offscreen for 0% CPU consumption
 * - Responsive to Chirpy light and dark modes
 */

(function () {
  'use strict';

  const TAU = Math.PI * 2;
  const BUCKETS = 20;

  // 13-point botanical polar spline anchors for Hedera helix
  const IVY_ANCHORS = [
    { a: 0, r: 1.0 },     // Apex tip
    { a: 22, r: 0.88 },
    { a: 38, r: 0.58 },   // Sinus 1
    { a: 54, r: 0.84 },   // Lateral lobe tip
    { a: 70, r: 0.64 },
    { a: 86, r: 0.40 },   // Sinus 2
    { a: 102, r: 0.58 },
    { a: 116, r: 0.68 },  // Basal lobe tip
    { a: 135, r: 0.46 },
    { a: 155, r: 0.26 },
    { a: 172, r: 0.08 },  // Cordate cleft
    { a: 180, r: 0.01 }   // Petiole insertion
  ];

  function getIvyRadius(deg, seed) {
    deg = Math.abs(deg) % 360;
    if (deg > 180) deg = 360 - deg;
    for (let i = 0; i < IVY_ANCHORS.length - 1; i++) {
      const p0 = IVY_ANCHORS[i];
      const p1 = IVY_ANCHORS[i + 1];
      if (deg >= p0.a && deg <= p1.a) {
        const t = (deg - p0.a) / (p1.a - p0.a);
        const st = t * t * (3 - 2 * t);
        const baseR = p0.r + (p1.r - p0.r) * st;
        const undul = 1 + 0.035 * Math.sin(((deg * 4 + (seed || 0) * 45) * Math.PI) / 180);
        return baseR * undul;
      }
    }
    return 0;
  }

  function distToSegment(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len2 = dx * dx + dy * dy;
    if (len2 === 0) return Math.hypot(px - x1, py - y1);
    const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / len2));
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
  }

  function rng(seed) {
    return function () {
      seed |= 0;
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function mix(a, b, t) {
    return [
      Math.round(a[0] + (b[0] - a[0]) * t),
      Math.round(a[1] + (b[1] - a[1]) * t),
      Math.round(a[2] + (b[2] - a[2]) * t)
    ];
  }

  function css(rgb) {
    return 'rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')';
  }

  function parseHex(hex) {
    hex = hex.replace('#', '').trim();
    if (/^[0-9a-f]{6}$/i.test(hex)) {
      return [0, 2, 4].map(function (i) { return parseInt(hex.slice(i, i + 2), 16); });
    }
    return [47, 138, 99];
  }

  function hexGrid(w, h, grid, cb) {
    const rowH = grid * 0.866025;
    const rows = Math.ceil(h / rowH) + 1;
    const cols = Math.ceil(w / grid) + 1;
    for (let r = 0; r < rows; r++) {
      const y = r * rowH;
      const xOff = (r % 2) * (grid * 0.5);
      for (let c = 0; c < cols; c++) {
        const x = c * grid + xOff;
        cb(x, y);
      }
    }
  }

  class IvyHalftoneEngine {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d', { alpha: true });
      this.grid = 8;
      this.w = 0;
      this.h = 0;
      this.dots = [];
      this.ramps = [];
      this.visible = false;
      this.last = 0;
      this.motionReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      this.theme();
      this.resize();
    }

    isDarkMode() {
      const htmlMode = document.documentElement.getAttribute('data-mode');
      if (htmlMode) return htmlMode === 'dark';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    theme() {
      const dark = this.isDarkMode();
      const paletteHex = dark
        ? [
            ['#2f8a63', '#5cc08e', '#4fb7be', '#2f8a63'],
            ['#a6e3bf', '#c3cfae', '#5cc08e'],
            ['#5cc08e', '#a6e3bf', '#c3cfae'],
            ['#0e0e18', '#7c80f0', '#a895ff', '#0e0e18'],
            ['#a7b86f', '#d39a6a', '#e0b27a']
          ]
        : [
            ['#1d5e47', '#2f8a63', '#1f7c83', '#1d5e47'],
            ['#74bf93', '#8e9f78', '#2f8a63'],
            ['#2f8a63', '#74bf93', '#8e9f78'],
            ['#17162b', '#3b3fb6', '#6c58c9', '#17162b'],
            ['#5a6a2c', '#7a4a2b', '#c29058']
          ];

      this.ramps = paletteHex.map(function (hexStops) {
        const stops = hexStops.map(parseHex);
        return Array.from({ length: BUCKETS }, function (_, i) {
          const f = (i / (BUCKETS - 1)) * (stops.length - 1);
          const a = Math.floor(f);
          return css(mix(stops[a], stops[Math.min(stops.length - 1, a + 1)], f - a));
        });
      });
    }

    resize() {
      const rect = this.canvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.w = rect.width;
      this.h = rect.height;
      this.canvas.width = Math.round(rect.width * dpr);
      this.canvas.height = Math.round(rect.height * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.build();
    }

    build() {
      const rand = rng(99);
      this.dots = [];
      const w = this.w;
      const h = this.h;
      if (!w || !h) return;

      const padX = Math.max(28, w * 0.05);
      const padY = Math.max(38, h * 0.16);
      const safeW = w - 2 * padX;
      const safeH = h - 2 * padY;

      const cy = h * 0.50;
      const P0 = [padX + safeW * 0.03, cy + safeH * 0.07];
      const P1 = [padX + safeW * 0.35, cy - safeH * 0.20];
      const P2 = [padX + safeW * 0.65, cy + safeH * 0.20];
      const P3 = [padX + safeW * 0.97, cy - safeH * 0.06];

      function bezier(t) {
        const u = 1 - t;
        return [
          u*u*u*P0[0] + 3*u*u*t*P1[0] + 3*u*t*t*P2[0] + t*t*t*P3[0],
          u*u*u*P0[1] + 3*u*u*t*P1[1] + 3*u*t*t*P2[1] + t*t*t*P3[1]
        ];
      }
      function tangent(t) {
        const u = 1 - t;
        const dx = 3*u*u*(P1[0]-P0[0]) + 6*u*t*(P2[0]-P1[0]) + 3*t*t*(P3[0]-P2[0]);
        const dy = 3*u*u*(P1[1]-P0[1]) + 6*u*t*(P2[1]-P1[1]) + 3*t*t*(P3[1]-P2[1]);
        const len = Math.hypot(dx, dy) || 1;
        return [dx / len, dy / len];
      }

      const stemSegments = Array.from({ length: 180 }, function (_, i) { return bezier(i / 179); });
      const S = Math.min(safeW * 0.18, safeH * 0.48);

      const leafSpecs = [
        { t: 0.14, side: -1, scale: 0.88 * S, young: false, angleOff: -0.22, pitch: 0.92, seed: 1 },
        { t: 0.30, side:  1, scale: 0.96 * S, young: false, angleOff:  0.18, pitch: 0.88, seed: 2 },
        { t: 0.50, side: -1, scale: 0.92 * S, young: false, angleOff: -0.15, pitch: 0.94, seed: 3 },
        { t: 0.68, side:  1, scale: 0.84 * S, young: false, angleOff:  0.22, pitch: 0.86, seed: 4 },
        { t: 0.84, side: -1, scale: 0.68 * S, young: true,  angleOff: -0.18, pitch: 0.95, seed: 5 },
        { t: 0.95, side:  1, scale: 0.52 * S, young: true,  angleOff:  0.25, pitch: 0.90, seed: 6 }
      ];

      const leaves = leafSpecs.map(function (ls) {
        const pt = bezier(ls.t);
        const tan = tangent(ls.t);
        const normal = [-tan[1] * ls.side, tan[0] * ls.side];
        const petioleL = ls.scale * 0.32;
        const petioleEnd = [pt[0] + normal[0] * petioleL, pt[1] + normal[1] * petioleL];
        const angle = Math.atan2(normal[1], normal[0]) + ls.angleOff;
        return {
          stemBase: pt,
          leafBase: petioleEnd,
          scale: ls.scale,
          young: ls.young,
          pitch: ls.pitch,
          seed: ls.seed,
          cos: Math.cos(angle),
          sin: Math.sin(angle)
        };
      });

      const ptU = bezier(0.42);
      const tanU = tangent(0.42);
      const peduncleEnd = [ptU[0] + tanU[1] * 0.28 * S, ptU[1] - tanU[0] * 0.28 * S];
      const berries = Array.from({ length: 12 }, function (_, i) {
        const a = (i / 12) * TAU + rand() * 0.22;
        const dist = (0.05 + 0.045 * rand()) * S;
        return {
          x: peduncleEnd[0] + Math.cos(a) * dist,
          y: peduncleEnd[1] + Math.sin(a) * dist,
          r: (0.026 + 0.005 * rand()) * S
        };
      });

      const rootlets = [0.18, 0.36, 0.56, 0.74].map(function (t) {
        const pt = bezier(t);
        const tan = tangent(t);
        return { x: pt[0] - tan[1] * 0.02 * S, y: pt[1] + tan[0] * 0.02 * S };
      });

      const grid = this.grid;
      const self = this;
      hexGrid(w, h, grid, function (px, py) {
        const k = rand();
        const p = px * 0.012 + py * 0.008;

        for (let i = 0; i < berries.length; i++) {
          const b = berries[i];
          const d = Math.hypot(px - b.x, py - b.y);
          if (d < b.r) {
            const u = (px - b.x) / b.r;
            const v = (py - b.y) / b.r;
            const spec = Math.hypot(u + 0.35, v + 0.35);
            const disc = Math.hypot(u - 0.22, v - 0.22);
            if (disc < 0.22) {
              self.dots.push({ x: px, y: py, r: (grid / 2) * 0.38, g: 1, p: p, k: k });
              return;
            }
            const rad = (grid / 2) * (spec < 0.24 ? 0.30 : 0.86) * (0.92 + k * 0.16);
            self.dots.push({ x: px, y: py, r: rad, g: 3, p: p, k: k });
            return;
          }
          if (distToSegment(px, py, peduncleEnd[0], peduncleEnd[1], b.x, b.y) < grid * 0.30) {
            self.dots.push({ x: px, y: py, r: grid * 0.20, g: 4, p: p, k: k });
            return;
          }
        }
        if (distToSegment(px, py, ptU[0], ptU[1], peduncleEnd[0], peduncleEnd[1]) < grid * 0.40) {
          self.dots.push({ x: px, y: py, r: grid * 0.28, g: 4, p: p, k: k });
          return;
        }

        for (let j = 0; j < leaves.length; j++) {
          const leaf = leaves[j];
          const rx = px - leaf.leafBase[0];
          const ry = py - leaf.leafBase[1];
          const lx = (rx * leaf.cos + ry * leaf.sin) / leaf.scale;
          const ly = (-rx * leaf.sin + ry * leaf.cos) / (leaf.scale * leaf.pitch);

          const dist = Math.hypot(lx, ly);
          if (dist > 1.05) continue;

          const deg = (Math.atan2(ly, lx) * 180) / Math.PI;
          const bladeR = getIvyRadius(deg, leaf.seed);

          if (dist <= bladeR && bladeR > 0.02) {
            const midribD = Math.abs(ly);
            const rad54 = (54 * Math.PI) / 180;
            const lat1D = distToSegment(lx, ly, 0, 0, 0.86 * Math.cos(rad54), 0.86 * Math.sin(rad54));
            const lat2D = distToSegment(lx, ly, 0, 0, 0.86 * Math.cos(-rad54), 0.86 * Math.sin(-rad54));
            const rad116 = (116 * Math.PI) / 180;
            const bas1D = distToSegment(lx, ly, 0, 0, 0.68 * Math.cos(rad116), 0.68 * Math.sin(rad116));
            const bas2D = distToSegment(lx, ly, 0, 0, 0.68 * Math.cos(-rad116), 0.68 * Math.sin(-rad116));

            const secPhase = ((lx + 0.05) % 0.17) / 0.17;
            const isSecVein = lx > 0.14 && lx < 0.76 && Math.abs(secPhase - 0.5) < 0.08 && Math.abs(ly) < 0.26;
            const isPrimaryVein = (midribD < 0.028 && lx < 0.95) || lat1D < 0.024 || lat2D < 0.024 || bas1D < 0.022 || bas2D < 0.022;

            if (isPrimaryVein || isSecVein) {
              self.dots.push({ x: px, y: py, r: (grid / 2) * 0.38, g: 1, p: p, k: k });
              return;
            }

            const fBlade = dist / bladeR;
            const shade = 0.45 + 0.55 * (1 - Math.pow(fBlade, 1.3));
            const rad = (grid / 2) * (0.48 + 0.48 * shade) * (0.92 + k * 0.16);
            self.dots.push({ x: px, y: py, r: rad, g: leaf.young ? 2 : 0, p: p, k: k });
            return;
          }

          if (distToSegment(px, py, leaf.stemBase[0], leaf.stemBase[1], leaf.leafBase[0], leaf.leafBase[1]) < grid * 0.36) {
            self.dots.push({ x: px, y: py, r: grid * 0.24, g: 4, p: p, k: k });
            return;
          }
        }

        for (let rk = 0; rk < rootlets.length; rk++) {
          const root = rootlets[rk];
          if (Math.hypot(px - root.x, py - root.y) < grid * 0.75) {
            self.dots.push({ x: px, y: py, r: grid * 0.20, g: 4, p: p, k: k });
            return;
          }
        }

        let minD = Infinity;
        let closestT = 0;
        for (let si = 0; si < stemSegments.length - 1; si++) {
          const sd = distToSegment(px, py, stemSegments[si][0], stemSegments[si][1], stemSegments[si + 1][0], stemSegments[si + 1][1]);
          if (sd < minD) {
            minD = sd;
            closestT = si / (stemSegments.length - 1);
          }
        }
        const stemThick = grid * (0.42 - 0.18 * closestT);
        if (minD < stemThick) {
          self.dots.push({ x: px, y: py, r: grid * (0.34 - 0.10 * closestT), g: 4, p: p, k: k });
        }
      });
    }

    draw(t) {
      const ctx = this.ctx;
      const w = this.w;
      const h = this.h;
      if (!w || !h) return;
      ctx.clearRect(0, 0, w, h);

      const dots = this.dots;
      const buckets = this.ramps.map(function () {
        return Array.from({ length: BUCKETS }, function () { return []; });
      });

      for (let i = 0; i < dots.length; i++) {
        const d = dots[i];
        const wave = 0.5 + 0.5 * Math.sin(d.p - t * 0.0006 + d.k * 1.3);
        const bIdx = Math.min(BUCKETS - 1, Math.floor(wave * BUCKETS));
        buckets[d.g][bIdx].push(d);
      }

      for (let g = 0; g < buckets.length; g++) {
        const ramp = this.ramps[g];
        for (let b = 0; b < BUCKETS; b++) {
          const list = buckets[g][b];
          if (!list.length) continue;
          ctx.fillStyle = ramp[b];
          ctx.beginPath();
          for (let j = 0; j < list.length; j++) {
            const d = list[j];
            ctx.moveTo(d.x + d.r, d.y);
            ctx.arc(d.x, d.y, d.r, 0, TAU);
          }
          ctx.fill();
        }
      }
    }
  }

  function init() {
    const canvas = document.getElementById('ivyFinialCanvas');
    if (!canvas) return;

    const engine = new IvyHalftoneEngine(canvas);

    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        engine.visible = e.isIntersecting;
      });
    });
    io.observe(canvas);

    const ro = new ResizeObserver(function () {
      engine.resize();
      engine.draw(performance.now());
    });
    ro.observe(canvas);

    const themeObserver = new MutationObserver(function () {
      engine.theme();
      engine.draw(performance.now());
    });
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-mode']
    });

    function loop(t) {
      if (engine.visible && !engine.motionReduced && t - engine.last > 32) {
        engine.last = t;
        engine.draw(t);
      }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);

    if (engine.motionReduced) {
      engine.draw(0);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
