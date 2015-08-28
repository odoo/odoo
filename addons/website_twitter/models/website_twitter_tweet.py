# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class WebsiteTwitterTweet(osv.osv):
    _name = "website.twitter.tweet"
    _description = "Twitter Tweets"
    _columns = {
        'website_id': fields.many2one('website', string="Website"),
        'screen_name': fields.char("Screen Name"),
        'tweet': fields.text('Tweets'),

        # Twitter IDs are 64-bit unsigned ints, so we need to store them in
        # unlimited precision NUMERIC columns, which can be done with a
        # float field. Used digits=(0,0) to indicate unlimited.
        # Using VARCHAR would work too but would have sorting problems.  
        'tweet_id': fields.float("Tweet ID", digits=(0,0)), # Twitter
    }
