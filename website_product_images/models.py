# -*- coding: utf-8 -*-
from openerp import tools
from openerp import models, fields, api
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
import pprint
_logger = logging.getLogger(__name__)

class optima_product(osv.Model):
      _inherit = 'product.template'
      def _get_image2(self, cr, uid, ids, name, args, context=None):
        #_logger.info('Dumping name is...........................:%s' %name)
        #_logger.info('Dumping get_image IDS ...........................:%s' %ids)
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image2, avoid_resize_medium=True)
            result[obj.id]['image_medium2'] = result[obj.id]['image_medium']
            result[obj.id]['image_small2'] = result[obj.id]['image_small']
            result[obj.id]['image_medium'] = False
            result[obj.id]['image_small'] = False
            #_logger.info('Dumping get_image2 results...........................:%s' %result)
        return result

      def _set_image2(self, cr, uid, id, name, value, args, context=None):
        res = self.write(cr, uid, [id], {'image2': tools.image_resize_image_big(value)}, context=context)
        #_logger.info('Dumping set_image2  name is *************************************:%s' %name)
        #_logger.info('Dumping set_image2  ID is *************************************:%s' %id)
        return res
      ###############################################################################################
      def _get_image3(self, cr, uid, ids, name, args, context=None):
        #_logger.info('Dumping _get_image3 name is...........................:%s' %name)
        #_logger.info('Dumping get_image3 IDS ...........................:%s' %ids)
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image3, avoid_resize_medium=True)
            result[obj.id]['image_medium3'] = result[obj.id]['image_medium']
            result[obj.id]['image_small3'] = result[obj.id]['image_small']
            result[obj.id]['image_medium'] = False
            result[obj.id]['image_small'] = False
            _logger.info('Dumping get_image3 results...........................:%s' %result)
        return result

      def _set_image3(self, cr, uid, id, name, value, args, context=None):
        res = self.write(cr, uid, [id], {'image3': tools.image_resize_image_big(value)}, context=context)
        #_logger.info('Dumping set_image3  name is *************************************:%s' %name)
        #_logger.info('Dumping set_image3  ID is *************************************:%s' %id)
        return res


      _columns = {
      'image2' : fields.binary("Image Two", help="This holds the second image of the product, Limited to 1024x1024 px"),
      'image_medium2' : fields.function(_get_image2, fnct_inv=_set_image2,
            string="Medium-sized image two", type="binary", multi="_get_image2",
            store={
                'product.template': (lambda self, cr, uid, ids, c={}: ids, ['image2'], 10),
            },
            help="Medium-sized image 2  of the product. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved, "\
                 "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
      'image_small2' : fields.function(_get_image2, fnct_inv=_set_image2,
            string="Small-sized image 2", type="binary", multi="_get_image2",
            store={
                'product.template': (lambda self, cr, uid, ids, c={}: ids, ['image2'], 10),
            },
            help="Small-sized image 2 of the product. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
      'image3' : fields.binary("Image three", help="This holds the second image of the product, imited to 1024x1024 px"),
      'image_medium3' : fields.function(_get_image3, fnct_inv=_set_image3,
            string="Medium-sized image 3", type="binary", multi="_get_image3",
            store={
                'product.template': (lambda self, cr, uid, ids, c={}: ids, ['image3'], 10),
            },
            help="Medium-sized image 3 of the product. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved, "\
                 "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
      'image_small3' : fields.function(_get_image3, fnct_inv=_set_image3,
            string="Small-sized image 3", type="binary", multi="_get_image3",
            store={
                'product.template': (lambda self, cr, uid, ids, c={}: ids, ['image3'], 10),
            },
            help="Small-sized image 3 of the product. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
     }



