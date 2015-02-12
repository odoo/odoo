from . import test_website_version_base


class TestWebsiteVersionAll(test_website_version_base.TestWebsiteVersionBase):

    def test_copy_version(self):
        """ Testing version_copy"""
        view_0_0_0_0_id, version_id, website_id = self.view_0_0_0_0.id, self.version.id, self.website.id

        copy_version = self.website_version_version.create({'name': 'copy_version_0_0_0_0', 'website_id': website_id})
        self.version.copy_version(copy_version.id)
        view_copy_version = copy_version.view_ids[0]
        self.env.context = {'version_id': version_id}
        view_0_0_0_0 = self.ir_ui_view.browse(view_0_0_0_0_id)
        self.assertEqual(view_copy_version.arch, view_0_0_0_0.arch, 'website_version: copy_version: website_version must have in snpashot_copy the same views then in version_0_0_0_0')
