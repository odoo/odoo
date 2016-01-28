# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Nicolas Bessi (Camptocamp)

import openerp

class WebKitHelper(object):
    """Set of usefull report helper"""
    def __init__(self, cursor, uid, report_id, context):
        "constructor"
        self.cursor = cursor
        self.uid = uid
        self.pool = openerp.registry(self.cursor.dbname)
        self.report_id = report_id
        self.context = context
        
    def embed_image(self, type, img, width=0, height=0) :
        "Transform a DB image into an embedded HTML image"

        if width :
            width = 'width="%spx"'%(width)
        else :
            width = ' '
        if height :
            height = 'height="%spx"'%(height)
        else :
            height = ' '
        toreturn = '<img %s %s src="data:image/%s;base64,%s" />'%(
            width,
            height,
            type, 
            str(img))
        return toreturn
            
            
    def get_logo_by_name(self, name):
        """Return logo by name"""
        header_obj = self.pool.get('ir.header_img')
        header_img_id = header_obj.search(
                                            self.cursor, 
                                            self.uid, 
                                            [('name','=',name)]
                                        )
        if not header_img_id :
            return u''
        if isinstance(header_img_id, list):
            header_img_id = header_img_id[0]

        head = header_obj.browse(self.cursor, self.uid, header_img_id)
        return (head.img, head.type)
            
    def embed_logo_by_name(self, name, width=0, height=0):
        """Return HTML embedded logo by name"""
        img, type = self.get_logo_by_name(name)
        return self.embed_image(type, img, width, height)

    def embed_company_logo(self, width=0, height=0):
        cr, uid, context = self.cursor, self.uid, self.context
        my_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        logo = my_user.company_id.logo_web
        return self.embed_image("png", logo, width, height)

        
