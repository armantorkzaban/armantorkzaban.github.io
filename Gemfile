# frozen_string_literal: true

source "https://rubygems.org"

gemspec

gem "html-proofer", "5.0.10"
gem "nokogiri", "1.18.7"
gem "pdf-reader", "2.14.1"
gem "typhoeus", "1.4.1"
# ...add other gems as needed...

platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end

gem "wdm", "~> 0.2.0", :platforms => [:mingw, :x64_mingw, :mswin]
