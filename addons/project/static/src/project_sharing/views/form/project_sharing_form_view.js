/** @odoo-module */

import { formView } from '@web/views/form/form_view';
import { ProjectSharingFormController } from './project_sharing_form_controller';
import { ProjectSharingFormRenderer } from './project_sharing_form_renderer';
import { ProjectSharingControlPanel } from '../../components/control_panel/project_sharing_control_panel';

formView.Controller = ProjectSharingFormController;
formView.Renderer = ProjectSharingFormRenderer;
formView.ControlPanel = ProjectSharingControlPanel;
