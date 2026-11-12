import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# XML ID prefix of the menus declared by this module.
_OUR_MODULE = "od19_website"

# Default Odoo website menus (declared by the ``website``, ``website_blog``,
# ``website_hr_recruitment`` ... modules) that duplicate our own navigation and
# must therefore be removed from the website header.
#
# They are matched by *URL* and not by *name*: the record name is translatable
# and is stored as "บล็อก" / "ติดต่อเรา" / "งาน" in a Thai database, so a
# name-based filter silently fails.  The URL is language independent and is
# also shared by the un-xmlided copies Odoo creates under the website's own top
# menu, so a single check catches both the template and the copy.
DEFAULT_MENU_URLS = {
    "/blog",
    "/jobs",
    "/our-job-offers",
    "/contactus",
    "/shop",
    "/events",
    "/forum",
}


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    @api.model
    def od19_configure_menus(self):
        """Re-parent and clean up the website's top navigation.

        ``website.menu_id`` is a computed (non-stored) field resolving to the
        first top-level ``website.menu`` (``parent_id = False``) belonging to
        the website.  The shared ``website.main_menu`` record has
        ``website_id = False`` and is *not* the website root, so menus declared
        under it would never render.

        This method is called both from the module's ``post_init_hook`` and
        from a ``<function>`` tag in ``data/website_menus.xml`` so it is applied
        on every install **and** on every module upgrade.
        """
        website = self.env.ref("website.default_website", raise_if_not_found=False)
        if not website:
            _logger.warning("Default website not found, skipping menu configuration.")
            return

        top_menu = website.menu_id
        if not top_menu:
            _logger.warning("Website %s has no top-level menu; skipping.", website.name)
            return

        menu_model = self.env["website.menu"].sudo()
        data_model = self.env["ir.model.data"].sudo()
        main_menu = self.env.ref("website.main_menu", raise_if_not_found=False)

        # 1) Identify *our* menus through their XML ID.  This keeps working
        #    whatever language the record names were translated to.
        our_data = data_model.search([
            ("model", "=", "website.menu"),
            ("module", "=", _OUR_MODULE),
        ])
        our_menus = menu_model.browse([d.res_id for d in our_data]).exists()
        our_ids = set(our_menus.ids)

        # 2) Re-parent our own top-level menus that still hang off the shared
        #    main menu onto the website's real top-level menu (e.g. "Careers").
        #    Sub-menus (Industrial / Building / Terminal Automation) keep their
        #    "Services" parent untouched.
        if main_menu:
            orphans = our_menus.filtered(lambda m: m.parent_id.id == main_menu.id)
            if orphans:
                orphans.write({"parent_id": top_menu.id})
                _logger.info("Re-parented %d menu(s) to the website top menu.", len(orphans))

        # 3) Remove the default Odoo menus that duplicate our navigation.  Both
        #    the shared template records (under ``main_menu``) and the copies
        #    hanging off the website top menu are removed.  Our own menus are
        #    always skipped, whatever their URL, so a real page such as
        #    "/blog" that we intentionally expose is never deleted.
        parent_ids = [top_menu.id]
        if main_menu:
            parent_ids.append(main_menu.id)
        candidates = menu_model.search([("parent_id", "in", parent_ids)])
        defaults = candidates.filtered(
            lambda m: m.id not in our_ids
            and (m.url or "").strip().split("?")[0].rstrip("/") in DEFAULT_MENU_URLS
        )
        if defaults:
            _logger.info("Removed %d default website menu item(s).", len(defaults))
            # ``website.menu.unlink()`` (website/models/website_menu.py) also
            # deletes *every* menu sharing the same URL once one of its records
            # is attached to the shared ``website.main_menu``.  Deleting the
            # default "/blog" entry would therefore also sweep away our own
            # "News & Events" menu pointing to the same page.  Detaching the
            # duplicates from ``main_menu`` first disarms that cascade, so
            # exactly the records selected above are removed.
            defaults.write({"parent_id": False})
            defaults.unlink()

        # 4) Remove Odoo's built-in "Home" menu.  It also points to "/" and,
        #    like our own "Home", is a child of the website top menu, so the
        #    header used to show two "Home" entries.  It is targeted through its
        #    XML ID instead of DEFAULT_MENU_URLS: the "/" url normalises to an
        #    empty string in the check above, which would then also match menus
        #    that legitimately carry no url at all.
        builtin_home = self.env.ref("website.menu_home", raise_if_not_found=False)
        if builtin_home and builtin_home.id not in our_ids:
            # Same cascade guard as above: detach it from the shared main menu
            # first, otherwise its unlink() also removes our own "/" menu.
            builtin_home.write({"parent_id": False})
            builtin_home.unlink()
            _logger.info("Removed the built-in Odoo \"Home\" menu item.")

        # 5) Drop the legacy "Employee Portal" top-level menu.  Up to SP1 it sat
        #    in the public navigation, but the page is staff-only
        #    (``auth="user"``), so it now lives in the footer instead.  It is
        #    targeted through its XML ID: on a fresh install the record is no
        #    longer declared, while on an upgrade the leftover copy (the menu
        #    block is ``noupdate="1"``, so removing the record from the data file
        #    alone does not delete it) is removed here.  Same cascade guard as
        #    above: detach from the shared main menu before unlinking.
        legacy_portal = self.env.ref(
            "od19_website.menu_employee_portal", raise_if_not_found=False
        )
        if legacy_portal:
            legacy_portal.write({"parent_id": False})
            legacy_portal.unlink()
            _logger.info("Removed the legacy \"Employee Portal\" top-level menu item.")
