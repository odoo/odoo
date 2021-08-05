# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import HttpCase

@odoo.tests.tagged('-at_install', 'post_install')
class TestImLivechatSupportPage(HttpCase):
    def test_load_modules(self):
        """Checks that all javascript modules load correctly on the livechat support page"""
        test_ready = """
            if (!window.testSetupHasRun) {
                window.testSetupHasRun = true;
                const setReady = () => odoo.__DEBUG__.didLogInfo.then(() => {
                    window.testIsReady = true;
                });
                if (document.readyState === "complete") {
                    setReady();
                } else {
                    window.addEventListener("load", setReady);
                }
            }
            window.testIsReady;
        """

        check_js_modules = """
            const { missing, failed, unloaded } = odoo.__DEBUG__.jsModules;
            if ([missing, failed, unloaded].some(arr => arr.length)) {
                console.error("Couldn't load all JS modules.", JSON.stringify({ missing, failed, unloaded }));
            } else {
                console.log("test successful");
            }
        """
        self.browser_js("/im_livechat/support/1", code=check_js_modules, ready=test_ready)
