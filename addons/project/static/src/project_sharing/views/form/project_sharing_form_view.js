import { formView } from '@web/views/form/form_view';
import { ProjectTaskControlPanel } from "@project/views/project_task_control_panel/project_task_control_panel";
import { ProjectSharingFormController } from './project_sharing_form_controller';
import { ProjectSharingFormRenderer } from './project_sharing_form_renderer';

formView.Controller = ProjectSharingFormController;
formView.ControlPanel = ProjectTaskControlPanel;
formView.Renderer = ProjectSharingFormRenderer;
