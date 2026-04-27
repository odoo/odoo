/** @odoo-module */

import { Activity } from "@mail/core/web/activity";

import { Approval } from "@approvals/web/activity/approval";

Object.assign(Activity.components, { Approval });
