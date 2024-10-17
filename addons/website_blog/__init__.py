# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from .models.website import Website
from .models.website_blog import BlogBlog, BlogPost, BlogTag, BlogTagCategory
from .models.website_snippet_filter import WebsiteSnippetFilter
