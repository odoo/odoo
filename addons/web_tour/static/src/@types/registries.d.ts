declare module "registries" {
    interface TourStep {
        auto?: boolean;
        content: string;
        extra_trigger?: string;
        isCheck?: boolean;
        in_modal?: boolean;
        trigger: string;
        run: string | (() => (void | Promise<void>));
    }

    export interface ToursRegistryShape {
        test?: boolean;
        url: string;
        steps(): TourStep[];
    }

    export interface GlobalRegistryCategories {
        "web_tour.tours": ToursRegistryShape;
    }
}
