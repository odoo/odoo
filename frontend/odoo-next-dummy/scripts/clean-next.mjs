import { existsSync, rmSync } from "node:fs";
import { join } from "node:path";
import process from "node:process";

const nextDir = join(process.cwd(), ".next");

if (existsSync(nextDir)) {
  rmSync(nextDir, { recursive: true, force: true });
  console.log("[dev:fresh] cache .next removido");
} else {
  console.log("[dev:fresh] sem cache .next para remover");
}

