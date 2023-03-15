/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { TodoEditableBreadcrumbName } from "@todo/components/todo_editable_breadcrumb_name/todo_editable_breadcrumb_name";

/**
 *  The FormController is overridden to be able to manage the edition of the name of a to-do directly
 *  in the breadcrumb.
 */

export class TodoFormController extends FormController {}

Object.assign(TodoFormController.components, { TodoEditableBreadcrumbName });
TodoFormController.template = 'todo.TodoFormView';
