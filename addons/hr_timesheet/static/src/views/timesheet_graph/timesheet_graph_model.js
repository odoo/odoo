import { GraphModel } from "@web/views/graph/graph_model";

import { patchGraphModel } from "../graph_model_patch";

export class hrTimesheetGraphModel extends GraphModel {}
patchGraphModel(hrTimesheetGraphModel);
