# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.addons.website_slides.tests.test_ui_wslides import TestUiMemberInvited


@tests.tagged("-at_install", "post_install")
class TestPortalChatterLoadBundle(TestUiMemberInvited):
    def test_load_modules(self):
        self.channel.visibility = "members"
        check_js_modules = """
                    odoo.portalChatterReady.then(() => {
                        const { missing, failed, unloaded } = odoo.loader.findErrors();
                        if ([missing, failed, unloaded].some(arr => arr.length)) {
                            console.error("Couldn't load all JS modules.", JSON.stringify({ missing, failed, unloaded }));
                        } else {
                            console.log("test successful");
                        }
                        Object.assign(console, {
                            log: () => {},
                            error: () => {},
                            warn: () => {},
                        });
                    })
                """
        self.browser_js(
            self.portal_invite_url,
            code=check_js_modules,
            ready="odoo.portalChatterReady",
            login="portal",
        )
