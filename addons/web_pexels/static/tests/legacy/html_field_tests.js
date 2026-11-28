import { pexelsService } from "@web_pexels/pexels_service";
import { mediaDialogServices } from "@web_editor/../tests/html_field_tests";

// update the list of required services to open the media dialog
mediaDialogServices.pexels = pexelsService;
