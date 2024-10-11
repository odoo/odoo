import ts = require("typescript/lib/tsserverlibrary");

function init(modules: { typescript: typeof import("typescript/lib/tsserverlibrary") }) {
    const ts = modules.typescript;
  
    function create(info: ts.server.PluginCreateInfo) {
      const logger = info.project.projectService.logger;
      const depsMap = info.config.depsMap || {};
      const fileNameRe = /\/(?<module>\w+)\/static\/(?<subdir>\w+)\//
      function getFilenameInfo(fileName: string) {
        const m = fileName.match(fileNameRe);
        if (m) {
          return m.groups;
        }
        return {}
      }
      function getDependencies(moduleName: string|undefined) {
        if (!moduleName || !(moduleName in depsMap)) {
          return null;
        }
        return ["odoo", moduleName, ...(depsMap[moduleName] || [])]
      }
      function isImportOdooValid(originModuleName: string, data: ts.CompletionEntryData) {
        const deps = getDependencies(originModuleName);
        if (!deps) {
          return true;
        }
        const { moduleSpecifier, fileName } = data;
        if (moduleSpecifier) {
          return deps.some(d => moduleSpecifier.startsWith(`@${d}/`))
        } else if (fileName) {
          return deps.some(d => fileName.includes(`/${d}/static/`))
        }
        return true;
      }
  
      const proxy: ts.LanguageService = Object.create(null);
      for (let k of Object.keys(info.languageService) as Array<keyof ts.LanguageService>) {
        const x = info.languageService[k]!;
        proxy[k] = (...args: Array<{}>) => x.apply(info.languageService, args);
      }
  
      // Remove specified entries from completion list
      proxy.getCompletionsAtPosition = (fileName, position, options) => {
        const prior = info.languageService.getCompletionsAtPosition(fileName, position, options);
        if (!prior) return
        
        const fileNameInfo = getFilenameInfo(fileName);

        const oldLength = prior.entries.length;
        prior.entries = prior.entries.filter((e) => {
            if (e.data) {
                if (fileNameInfo.subdir === "src" && (e.data.fileName || "").includes("/tests/")) {
                  return false
                }
                return isImportOdooValid(fileNameInfo.module, e.data)
            }
            return true;
        });
  
        // Sample logging for diagnostic purposes
        if (oldLength !== prior.entries.length) {
          const entriesRemoved = oldLength - prior.entries.length;
          logger.info(
            `Removed ${entriesRemoved} entries from the completion list`
          );
        }
  
        return prior;
      };
  
      return proxy;
    }
  
    return { create };
  }
  
  export = init;
