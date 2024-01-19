# -*- coding: utf-8 -*-

import logging

from .test_project_base import TestProjectCommon

_logger = logging.getLogger(__name__)


class TestProjectConfig(TestProjectCommon):
    """Test module configuration and its effects on projects."""

    @classmethod
    def setUpClass(cls):
        super(TestProjectConfig, cls).setUpClass()
        cls.Project = cls.env["project.project"]
        cls.Settings = cls.env["res.config.settings"]
        cls.features = (
            # Pairs of associated (config_flag, project_flag)
            ("group_project_rating", "rating_active"),
            )

        # Start with a known value on feature flags to ensure validity of tests
        cls._set_feature_status(is_enabled=False)

    @classmethod
    def _set_feature_status(cls, is_enabled):
        """Set enabled/disabled status of all optional features in the
        project app config to is_enabled (boolean).
        """
        features_config = cls.Settings.create(
            {feature[0]: is_enabled for feature in cls.features})
        features_config.execute()

    def test_existing_projects_enable_features(self):
        """Check that *existing* projects have features enabled when
        the user enables them in the module configuration.
        """
        self._set_feature_status(is_enabled=True)
        for config_flag, project_flag in self.features:
            self.assertTrue(
                self.project_pigs[project_flag],
                "Existing project failed to adopt activation of "
                f"{config_flag}/{project_flag} feature")

    def test_new_projects_enable_features(self):
        """Check that after the user enables features in the module
        configuration, *newly created* projects have those features
        enabled as well.
        """
        self._set_feature_status(is_enabled=True)
        project_cows = self.Project.create({
            "name": "Cows",
            "partner_id": self.partner_1.id})
        for config_flag, project_flag in self.features:
            self.assertTrue(
                project_cows[project_flag],
                f"Newly created project failed to adopt activation of "
                f"{config_flag}/{project_flag} feature")

    def test_project_stages_feature_enable_views(self):
        """Check that the Gantt, Calendar and Activities views are
        enabled when the 'Project Stage' feature is enabled.
        """
        self.Settings.create({"group_project_stages": True}).execute() # enabling feature
        menu_ids = set([self.env.ref('project.menu_projects').id, self.env.ref('project.menu_projects_config').id])
        menu_loaded = set(self.env['ir.ui.menu']._load_menus_blacklist())
        self.assertTrue(menu_ids.issubset(menu_loaded), "The menu project and menu projects config should be loaded")
