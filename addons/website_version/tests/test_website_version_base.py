from openerp.tests import common

class TestWebsiteVersionBase(common.TransactionCase):

    def setUp(self):
        super(TestWebsiteVersionBase, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.ir_ui_view = self.registry('ir.ui.view')
        self.ir_qweb = self.registry('website.qweb')
        self.snapshot = self.registry('website_version.snapshot')
        self.website = self.registry('website')

        #Usefull objects
        master_view_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website', 'website2_homepage')
        self.master_view_id = master_view_ref and master_view_ref[1] or False
        self.arch_master=self.ir_ui_view.browse(cr, uid, [self.master_view_id], context=None)[0].arch
        snapshot_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website_version', 'snapshot_0_0_0_0')
        self.snapshot_id = snapshot_ref and snapshot_ref[1] or False
        website_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website', 'website2')
        self.website_id = website_ref and website_ref[1] or False
        view_0_0_0_0_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website_version', 'website2_homepage_other')
        self.view_0_0_0_0_id = view_0_0_0_0_ref and view_0_0_0_0_ref[1] or False
        self.arch_0_0_0_0 = self.ir_ui_view.browse(cr, uid, [self.view_0_0_0_0_id], context=None)[0].arch
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
                                <h2>Snapshot 0.0.0.0</h2>
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
