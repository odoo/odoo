odoo.define('mail.systray.ActivityMenu', function (require) {
    "use strict";

    const patchMixin = require("web.patchMixin");
    const SystrayMenu = require("web.SystrayMenu");

    const { useState } = owl.hooks;

    /**
     * Menu item appended in the systray part of the navbar, redirects to the next
     * activities of all app
     */
    class ActivityMenu extends owl.Component {
        constructor() {
            super(...arguments);
            this.state = useState({ activities: [] });
            this.env.bus.on("activity_updated", this, this._updateCounter);
        }

        mounted() {
            $(this.el).on("show.bs.dropdown", this._onActivityMenuShow.bind(this));
            $(this.el).on("hide.bs.dropdown", this._onActivityMenuHide.bind(this));
            this._activitiesPreview = this.el.querySelector(".o_mail_systray_dropdown_items");
            this._updateCounter();
            this._updateActivityPreview();
            return super.mounted();
        }

        //--------------------------------------------------
        // Private
        //--------------------------------------------------

        /**
         * Make RPC and get current user's activity details
         * @private
         */
        async _getActivityData() {
            await this.env.services
                .rpc({
                    model: "res.users",
                    method: "systray_get_activities",
                    args: [],
                    kwargs: { context: this.env.session.user_context },
                })
                .then((data) => {
                    this.state.activities = data;
                    this.activityCounter = data.reduce(function (total_count, p_data) {
                        return total_count + p_data.total_count || 0;
                    }, 0);
                    this.el.querySelector(
                        ".o_notification_counter"
                    ).innerText = this.activityCounter;
                    this.activityCounter
                        ? this.el.classList.remove("o_no_notification")
                        : this.el.classList.add("o_no_notification");
                });
        }
        /**
         * Get particular model view to redirect on click of activity scheduled on that model.
         * @private
         * @param {string} model
         */
        _getActivityModelViewID(model) {
            return this.env.services.rpc({
                model: model,
                method: "get_activity_view_id",
            });
        }
        /**
         * Return views to display when coming from systray depending on the model.
         *
         * @private
         * @param {string} model
         * @returns {Array[]} output the list of views to display.
         */
        _getViewsList(model) {
            return [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ];
        }
        /**
         * Update(render) activity system tray view on activity updation.
         * @private
         */
        async _updateActivityPreview() {
            await this._getActivityData();
        }
        /**
         * update counter based on activity status(created or Done)
         * @private
         * @param {Object} [data] key, value to decide activity created or deleted
         * @param {String} [data.type] notification type
         * @param {Boolean} [data.activity_deleted] when activity deleted
         * @param {Boolean} [data.activity_created] when activity created
         */
        _updateCounter(data) {
            if (data) {
                if (data.activity_created) {
                    this.activityCounter++;
                }
                if (data.activity_deleted && this.activityCounter > 0) {
                    this.activityCounter--;
                }
                this.el.querySelector(".o_notification_counter").innerText = this.activityCounter;
                this.activityCounter
                    ? this.el.classList.remove("o_no_notification")
                    : this.el.classList.add("o_no_notification");
            }
        }

        //------------------------------------------------------------
        // Handlers
        //------------------------------------------------------------

        /**
         * Redirect to specific action given its xml id or to the activity
         * view of the current model if no xml id is provided
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onActivityActionClick(ev) {
            $(this.el.querySelector(".dropdown-toggle")).dropdown("toggle");
            const targetAction = ev.currentTarget;
            const actionXmlid = targetAction.getAttribute("data-action_xmlid");
            if (actionXmlid) {
                this.trigger("do-action", {
                    action: actionXmlid,
                });
            } else {
                let domain = [["activity_ids.user_id", "=", this.env.session.uid]];
                if (targetAction.getAttribute("data-domain")) {
                    domain = domain.concat(targetAction.getAttribute("data-domain"));
                }

                this.trigger("do-action", {
                    action: {
                        type: "ir.actions.act_window",
                        name: targetAction.getAttribute("data-model_name"),
                        views: [
                            [false, "activity"],
                            [false, "kanban"],
                            [false, "list"],
                            [false, "form"],
                        ],
                        view_mode: "activity",
                        res_model: targetAction.getAttribute("data-res_model"),
                        domain: domain,
                    },
                });
            }
        }

        /**
         * Redirect to particular model view
         * @private
         * @param {MouseEvent} event
         */
        _onActivityFilterClick(event) {
            // fetch the data from the button otherwise fetch the ones from the parent (.o_mail_preview).
            const data = Object.assign({}, event.currentTarget.dataset, event.target.dataset);
            const context = {};
            if (data.filter === "my") {
                context["search_default_activities_overdue"] = 1;
                context["search_default_activities_today"] = 1;
            } else {
                context["search_default_activities_" + data.filter] = 1;
            }
            // Necessary because activity_ids of mail.activity.mixin has auto_join
            // So, duplicates are faking the count and "Load more" doesn't show up
            context["force_search_count"] = 1;

            var domain = [["activity_ids.user_id", "=", this.env.session.uid]];
            if (data.domain) {
                domain = domain.concat(data.domain);
            }

            this.trigger("do-action", {
                action: {
                    type: "ir.actions.act_window",
                    name: data.model_name,
                    res_model: data.res_model,
                    views: this._getViewsList(data.res_model),
                    search_view_id: [false],
                    domain: domain,
                    context: context,
                },
            });
        }
        /**
         * @private
         */
        _onActivityMenuShow() {
            document.body.classList.add("modal-open");
            this._updateActivityPreview();
        }
        /**
         * @private
         */
        _onActivityMenuHide() {
            document.body.classList.remove("modal-open");
        }
    }

    ActivityMenu.template = "mail.systray.ActivityMenu";
    // ActivityMenuOwl.name = "activity_menu";

    const PatchableActivityMenu = patchMixin(ActivityMenu);

    SystrayMenu.Items.push(PatchableActivityMenu);

    return PatchableActivityMenu;

});
