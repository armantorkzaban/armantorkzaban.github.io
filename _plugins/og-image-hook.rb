#!/usr/bin/env ruby
# frozen_string_literal: true

require 'cgi'

#
# Hook to automatically attach generated OG preview images and excerpts to Jekyll posts.
# Guarantees social sharing cards have large rich previews without rendering
# duplicate header banners on post articles (preview_only: true).
#

Jekyll::Hooks.register :posts, :post_init do |post|
  slug = post.data['slug'] || post.slug

  # 1. Attach OG preview image
  if post.data['image']
    if post.data['image'].is_a?(String)
      post.data['image'] = {
        'path' => post.data['image'],
        'alt' => post.data['title'] || 'Preview Image',
        'preview_only' => true
      }
    elsif post.data['image'].is_a?(Hash) && !post.data['image'].key?('preview_only')
      post.data['image']['preview_only'] = true
    end
  else
    og_filename = "#{slug}.png"
    og_file_path = File.join(post.site.source, 'assets', 'img', 'og', og_filename)

    if File.exist?(og_file_path)
      post.data['image'] = {
        'path' => "/assets/img/og/#{og_filename}",
        'alt' => post.data['title'] || 'Preview Image',
        'preview_only' => true
      }
    elsif post.site.config['social_preview_image']
      post.data['image'] = {
        'path' => post.site.config['social_preview_image'],
        'alt' => post.data['title'] || 'Social Preview',
        'preview_only' => true
      }
    end
  end

  # 2. Auto-generate clean description for SEO & OG if not provided in front matter
  if post.data['description'].nil? || post.data['description'].to_s.strip.empty?
    raw = post.content.to_s

    # Strip audio blocks and 'Listen to article' paragraphs
    clean = raw
      .gsub(/<audio[^>]*>[\s\S]*?<\/audio>/i, '')
      .gsub(/<p[^>]*>[\s\S]*?(?:گوش دادن به این مقاله|Listen to this article)[\s\S]*?<\/p>/i, '')
      .gsub(/&#9654;|\u25B6/, '')

    # Unescape HTML entities
    clean = CGI.unescapeHTML(clean)

    # Strip tags and formatting
    clean = clean
      .gsub(/<\/?(?:a|em|strong|b|i|span|code|small)[^>]*>/i, '')
      .gsub(/<[^>]+>/, ' ')
      .gsub(/!\[.*?\]\(.*?\)/, ' ')
      .gsub(/\[([^\]]+)\]\(.*?\)/, '\1')
      .gsub(/\{:[^}]+\}/, ' ')
      .gsub(/`{1,3}[^`]+`{1,3}/, ' ')
      .gsub(/[_*~>#]/, ' ')
      .gsub(/\s+/, ' ')
      .strip

    if clean.length > 0
      # Break at word boundary
      if clean.length > 160
        truncated = clean[0...160]
        last_space = truncated.rindex(' ')
        desc = last_space ? truncated[0...last_space] : truncated
        post.data['description'] = desc.sub(/[،.,;…\-_ ]+\z/, '') + '...'
      else
        post.data['description'] = clean
      end
    end
  end
end
