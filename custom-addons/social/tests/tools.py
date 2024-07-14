# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

try:
    from odoo.addons.social_facebook.models.social_account import SocialAccountFacebook
    from odoo.addons.social_facebook.models.social_live_post import SocialLivePostFacebook
    from odoo.addons.social_facebook.models.social_stream import SocialStreamFacebook
    is_facebook_module_installed = True
except ImportError:
    is_facebook_module_installed = False

try:
    from odoo.addons.social_instagram.models.social_account import SocialAccountInstagram
    from odoo.addons.social_instagram.models.social_live_post import SocialLivePostInstagram
    from odoo.addons.social_instagram.models.social_post import SocialPostInstagram
    from odoo.addons.social_instagram.models.social_stream import SocialStreamInstagram
    is_instagram_module_installed = True
except ImportError:
    is_instagram_module_installed = False

try:
    from odoo.addons.social_linkedin.models.social_account import SocialAccountLinkedin
    from odoo.addons.social_linkedin.models.social_live_post import SocialLivePostLinkedin
    from odoo.addons.social_linkedin.models.social_stream import SocialStreamLinkedIn
    is_linkedin_module_installed = True
except ImportError:
    is_linkedin_module_installed = False

try:
    from odoo.addons.social_twitter.models.social_account import SocialAccountTwitter
    from odoo.addons.social_twitter.models.social_live_post import SocialLivePostTwitter
    from odoo.addons.social_twitter.models.social_stream import SocialStreamTwitter
    is_twitter_module_installed = True
except ImportError:
    is_twitter_module_installed = False

try:
    from odoo.addons.social_youtube.models.social_account import SocialAccountYoutube
    from odoo.addons.social_youtube.models.social_live_post import SocialLivePostYoutube
    from odoo.addons.social_youtube.models.social_stream import SocialStreamYoutube
    is_youtube_module_installed = True
except ImportError:
    is_youtube_module_installed = False

@contextmanager
def mock_void_external_calls():
    """ Often, when testing social modules, we want to void all outgoing external calls methods.
    This method creates a handy context manager that will void all external calls at once. """
    with mock_void_external_calls_facebook(), \
         mock_void_external_calls_instagram(), \
         mock_void_external_calls_twitter(), \
         mock_void_external_calls_linkedin(), \
         mock_void_external_calls_youtube():
        yield

@contextmanager
def mock_void_external_calls_facebook():
    if is_facebook_module_installed:
        with patch.object(SocialAccountFacebook, '_compute_statistics', lambda x: None), \
             patch.object(SocialAccountFacebook, '_create_default_stream_facebook', lambda *args, **kwargs: None), \
             patch.object(SocialLivePostFacebook, '_post_facebook', lambda x: None), \
             patch.object(SocialStreamFacebook, '_fetch_stream_data', lambda x: None):
            yield
    else:
        yield

@contextmanager
def mock_void_external_calls_instagram():
    if is_instagram_module_installed:
        with patch.object(SocialAccountInstagram, '_compute_statistics', lambda x: None), \
             patch.object(SocialAccountInstagram, '_create_default_stream_instagram', lambda *args, **kwargs: None), \
             patch.object(SocialLivePostInstagram, '_post_instagram', lambda x: None), \
             patch.object(SocialPostInstagram, '_check_post_access', lambda x: False), \
             patch.object(SocialStreamInstagram, '_fetch_stream_data', lambda x: None):
            yield
    else:
        yield

@contextmanager
def mock_void_external_calls_linkedin():
    if is_linkedin_module_installed:
        with patch.object(SocialAccountLinkedin, '_compute_statistics', lambda x: None), \
             patch.object(SocialAccountLinkedin, '_create_default_stream_linkedin', lambda *args, **kwargs: None), \
             patch.object(SocialLivePostLinkedin, '_post_linkedin', lambda x: None), \
             patch.object(SocialStreamLinkedIn, '_fetch_stream_data', lambda x: None):
            yield
    else:
        yield

@contextmanager
def mock_void_external_calls_twitter():
    if is_twitter_module_installed:
        with patch.object(SocialAccountTwitter, '_compute_statistics', lambda x: None), \
             patch.object(SocialAccountTwitter, '_create_default_stream_twitter', lambda *args, **kwargs: None), \
             patch.object(SocialLivePostTwitter, '_post_twitter', lambda x: None), \
             patch.object(SocialStreamTwitter, '_fetch_stream_data', lambda x: None):
            yield
    else:
        yield

@contextmanager
def mock_void_external_calls_youtube():
    if is_youtube_module_installed:
        with patch.object(SocialAccountYoutube, '_create_default_stream_youtube', lambda *args, **kwargs: None), \
             patch.object(SocialLivePostYoutube, '_post_youtube', lambda x: None), \
             patch.object(SocialStreamYoutube, '_fetch_stream_data', lambda x: None):
            yield
    else:
        yield
