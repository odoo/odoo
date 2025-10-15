import { pick } from "@web/core/utils/objects";

export function getCategoriesAndSub(pos) {
    const displayableCategories = getDisplayableCategories(pos);
    const selectedCategory = pos.selectedCategory;
    const displayableCategoriesSet = new Set(displayableCategories);
    const rootCategories = displayableCategories
        .filter(
            (category) => !category.parent_id || !displayableCategoriesSet.has(category.parent_id)
        )
        .sort((a, b) => a.sequence - b.sequence);
    const selected = selectedCategory ? [selectedCategory] : [];
    const allParents = selected
        .concat(getAllParents(selectedCategory, displayableCategoriesSet))
        .reverse();
    return getCategoriesList(rootCategories, allParents, displayableCategoriesSet, 0)
        .flat(Infinity)
        .map((cat) => getChildCategoriesInfo(pos, cat, rootCategories, displayableCategoriesSet));
}

function getCategoriesList(list, allParents, displayableCategoriesSet, depth) {
    const categoriesList = [...list];
    list.forEach((item) => {
        if (item.id === allParents[depth]?.id) {
            const children = getChildren(item, displayableCategoriesSet);
            if (children.length) {
                categoriesList.push(
                    ...getCategoriesList(children, allParents, displayableCategoriesSet, depth + 1)
                );
            }
        }
    });
    return categoriesList;
}

function getDisplayableCategories(pos) {
    const { limit_categories, iface_available_categ_ids } = pos.config;
    if (limit_categories && iface_available_categ_ids.length > 0) {
        return iface_available_categ_ids;
    }
    return pos.models["pos.category"].getAll();
}

export function getAncestorsAndCurrent(selectedCategory, displayableCategoriesSet) {
    return selectedCategory
        ? [selectedCategory, ...getAllParents(selectedCategory, displayableCategoriesSet)]
        : [];
}

function getAllParents(category, displayableCategoriesSet) {
    return category?.allParents.filter((cat) => displayableCategoriesSet.has(cat)) || [];
}

function getChildren(category, displayableCategoriesSet) {
    return (
        category.child_ids
            ?.filter((child) => displayableCategoriesSet.has(child))
            .sort((a, b) => a.sequence - b.sequence) || []
    );
}

export function getChildCategoriesInfo(pos, category, rootCategories, displayableCategoriesSet) {
    const selectedCategory = pos.selectedCategory;

    return {
        ...pick(category, "id", "name", "color"),
        imgSrc:
            pos.config.show_category_images && category.has_image
                ? `/web/image?model=pos.category&field=image_128&id=${category.id}`
                : undefined,
        isSelected: getAncestorsAndCurrent(selectedCategory, displayableCategoriesSet).includes(
            category
        ),
        isChildren: (selectedCategory
            ? getChildren(selectedCategory, displayableCategoriesSet)
            : rootCategories
        ).includes(category),
    };
}
