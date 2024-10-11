"use strict";
function init(modules) {
    const ts = modules.typescript;
    function create(info) {
        const logger = info.project.projectService.logger;
        const depsMap = info.config.depsMap;
        const fileNameRe = /\/(?<module>\w+)\/static\/(?<subdir>\w+)\//;
        function getFilenameInfo(fileName) {
            const m = fileName.match(fileNameRe);
            if (m) {
                return m.groups;
            }
            return {};
        }
        function getDependencies(moduleName) {
            if (!moduleName || !(moduleName in depsMap)) {
                return null;
            }
            return ["odoo", moduleName, ...(depsMap[moduleName] || [])];
        }
        function isImportOdooValid(originModuleName, data) {
            const deps = getDependencies(originModuleName);
            if (!deps) {
                return true;
            }
            const { moduleSpecifier, fileName } = data;
            if (moduleSpecifier) {
                return deps.some(d => moduleSpecifier.startsWith(`@${d}/`));
            }
            else if (fileName) {
                return deps.some(d => fileName.includes(`/${d}/static/`));
            }
            return true;
        }
        const proxy = Object.create(null);
        for (let k of Object.keys(info.languageService)) {
            const x = info.languageService[k];
            proxy[k] = (...args) => x.apply(info.languageService, args);
        }
        // Remove specified entries from completion list
        proxy.getCompletionsAtPosition = (fileName, position, options) => {
            const prior = info.languageService.getCompletionsAtPosition(fileName, position, options);
            if (!prior)
                return;
            const fileNameInfo = getFilenameInfo(fileName);
            const oldLength = prior.entries.length;
            prior.entries = prior.entries.filter((e) => {
                if (e.data) {
                    if (fileNameInfo.subdir === "src" && (e.data.fileName || "").includes("/tests/")) {
                        return false;
                    }
                    return isImportOdooValid(fileNameInfo.module, e.data);
                }
                return true;
            });
            // Sample logging for diagnostic purposes
            if (oldLength !== prior.entries.length) {
                const entriesRemoved = oldLength - prior.entries.length;
                logger.info(`Removed ${entriesRemoved} entries from the completion list`);
            }
            return prior;
        };
        return proxy;
    }
    return { create };
}
module.exports = init;
