import { fields, models } from "@web/../tests/web_test_helpers";
import { websiteBuilderModels } from "@website/../tests/builder/website_helpers";

// the mega menu option asks for the public categories as soon as it mounts
class ProductPublicCategory extends models.Model {
    _name = "product.public.category";

    name = fields.Char();
    website_id = fields.Many2one({ relation: "website" });
}

websiteBuilderModels.push(ProductPublicCategory);
