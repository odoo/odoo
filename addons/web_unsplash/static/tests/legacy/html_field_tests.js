import { unsplashService } from "@web_unsplash/unsplash_service";
import { mediaDialogServices } from "@web_editor/../tests/html_field_tests";

// update the list of required services to open the media dialog
mediaDialogServices.unsplash = unsplashService;
