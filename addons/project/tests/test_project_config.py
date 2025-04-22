from .test_project_base import TestProjectCommon


class TestProjectConfig(TestProjectCommon):
    """Test module configuration and its effects on projects."""

    @classmethod
    def setUpClass(cls):
        super(TestProjectConfig, cls).setUpClass()
        cls.Settings = cls.env["res.config.settings"]

    def test_project_stages_feature_enable_views(self):
        """Check that the Gantt, Calendar and Activities views are
        enabled when the 'Project Stage' feature is enabled.
        """
        self.Settings.create({"group_project_stages": True}).execute() # enabling feature
        menu_ids = set([self.env.ref('project.menu_projects').id, self.env.ref('project.menu_projects_config').id])
        menu_loaded = set(self.env['ir.ui.menu']._load_menus_blacklist())
        self.assertTrue(menu_ids.issubset(menu_loaded), "The menu project and menu projects config should be loaded")
