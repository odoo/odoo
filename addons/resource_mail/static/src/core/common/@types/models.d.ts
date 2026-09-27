declare module "models" {
    import { ResourceResource as ResourceResourceClass } from "@resource_mail/core/common/resource_resource_model";

    export interface ResourceResource extends ResourceResourceClass {}

    export interface Store {
        "resource.resource": StaticMailRecord<ResourceResource, typeof ResourceResourceClass>;
    }

    export interface Models {
        "resource.resource": ResourceResource;
    }
}
