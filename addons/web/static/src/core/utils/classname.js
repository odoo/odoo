/**
 * Adds the given classes to an element, whether the classes
 * are strings or objects.
 *
 * @param {HTMLElement} el
 * @param {String|Object|undefined} classes
 *
 * @example
 * addClassesToElement(el, "hello", { "world": 0 == 1, }...)
 */
export function addClassesToElement(el, ...classes) {
    for (const classDefinition of classes) {
        const classObj = toClassObj(classDefinition);
        for (const className in classObj) {
            if (classObj[className]) {
                el.classList.add(className.trim());
            }
        }
    }
}

/**
 * Merges two classes to a single class object, whether the
 * classes are strings or objects.
 *
 * @param {String|Object|undefined} classes
 * @returns {Object}
 *
 * @example
 * mergeClasses("hello", { "world": 0 == 1, }...)
 */
export function mergeClasses(...classes) {
    const classObj = {};
    for (const classDefinition of classes) {
        Object.assign(classObj, toClassObj(classDefinition));
    }
    return classObj;
}

/**
 * Returns an object from a class definition, whether it
 * is a string or an object.
 *
 * The returned object keys are css class names and the
 * values are expressions which represent if the class
 * should be added or not.
 *
 * @param {String|Object|undefined} classDefinition
 * @returns {Object}
 */
function toClassObj(classDefinition) {
    if (!classDefinition) {
        return {};
    } else if (typeof classDefinition === "object") {
        return classDefinition;
    } else if (typeof classDefinition === "string") {
        const classObj = {};
        classDefinition
            .trim()
            .split(/\s+/)
            .forEach((s) => {
                classObj[s] = true;
            });
        return classObj;
    } else {
        console.warn(
            `toClassObj only supports strings, objects and undefined className (got ${typeof classProp})`
        );
        return {};
    }
}
