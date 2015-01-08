from openerp.tests import common

class TestWebsiteVersionBase(common.TransactionCase):

    def setUp(self):
        super(TestWebsiteVersionBase, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.ir_ui_view = self.env['ir.ui.view']
        self.website_version_version = self.env['website_version.version']
        self.website = self.env['website']
        self.ir_model_data = self.env['ir.model.data']

        #Usefull objects
        master_view = self.registry('ir.model.data').xmlid_to_object(cr, uid, 'website.website2_homepage', context=None)
        self.arch_master = master_view.arch
        self.version = self.registry('ir.model.data').xmlid_to_object(cr, uid, 'website_version.version_0_0_0_0', context=None)
        self.website = self.registry('ir.model.data').xmlid_to_object(cr, uid, 'website.website2', context=None)
        self.view_0_0_0_0 = self.registry('ir.model.data').xmlid_to_object(cr, uid, 'website_version.website2_homepage_other', context=None)
        self.arch_0_0_0_0 = self.view_0_0_0_0.arch
        self.vals = {'arch':
          """<t name="Homepage" priority="29" t-name="website.homepage">
            <t t-call="website.layout">
              <div id="wrap" class="oe_structure oe_empty">
                <div class="carousel slide mb32" id="myCarousel0" style="height: 320px;">
                  <ol class="carousel-indicators hidden">
                    <li class="active" data-slide-to="0" data-target="#myCarousel0"/>
                  </ol>
                  <div class="carousel-inner">
                    <div class="item image_text oe_img_bg active" style="background-image: url(http://0.0.0.0:8069/website/static/src/img/banner/mountains.jpg);">
                      <div class="container">
                        <div class="row content">
                          <div class="carousel-content col-md-6 col-sm-12">
                            <h2>version 0.0.0.0</h2>
                            <h3>Click to customize this text</h3>
                            <p>
                              <a class="btn btn-success btn-large" href="/page/website.contactus">Contact us</a>
                            </p>
                          </div>
                          <span class="carousel-img col-md-6 hidden-sm hidden-xs"> </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="carousel-control left hidden" data-slide="prev" data-target="#myCarousel0" href="#myCarousel0" style="width: 10%">
                    <i class="fa fa-chevron-left"/>
                  </div>
                  <div class="carousel-control right hidden" data-slide="next" data-target="#myCarousel0" href="#myCarousel0" style="width: 10%">
                    <i class="fa fa-chevron-right"/>
                  </div>
                </div>
              </div>
            </t>
          </t>"""
        }
