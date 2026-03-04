import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    include: ["src/tests/**/*.test.ts", "src/tests/**/*.test.tsx"],
    setupFiles: ["./vitest.setup.ts"]
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src")
    }
  }
});
