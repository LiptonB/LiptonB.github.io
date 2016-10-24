#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

from markdown.extensions.toc import TocExtension
from markdown.extensions.codehilite import CodeHiliteExtension

AUTHOR = u'Benjamin Lipton'
SITENAME = u'bl stash save'
SITEURL = ''

PATH = 'content'

STATIC_PATHS = ['images', 'extra/CNAME']
EXTRA_PATH_METADATA = {'extra/CNAME': {'path': 'CNAME'}}

TIMEZONE = 'America/New_York'

DEFAULT_LANG = u'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

FILENAME_METADATA = '(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>[^.]*)'
ARTICLE_URL = '{date:%Y}/{date:%m}/{date:%d}/{slug}.html'
ARTICLE_SAVE_AS = '{date:%Y}/{date:%m}/{date:%d}/{slug}.html'

# Blogroll
# LINKS = (('Pelican', 'http://getpelican.com/'),
#          ('Python.org', 'http://python.org/'),
#          ('Jinja2', 'http://jinja.pocoo.org/'),
#          ('You can modify those links in your config file', '#'),)

# Social widget
SOCIAL = (('You can add links in your config file', '#'),
          ('Another social link', '#'),)

DEFAULT_PAGINATION = False

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
MD_EXTENSIONS = [TocExtension(), CodeHiliteExtension(css_class='highlight', guess_lang=False)]
THEME = '../pelican-themes/alchemy/alchemy'
