declare module "registries" {
    interface TourStep {
        content: string;
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
