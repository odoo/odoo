import { GovDetailView } from "@/components/gov/gov-detail-view";
import { StatusState } from "@/components/ui/status-state";
import { getGovSuiteBySlug } from "@/lib/gov-suite";

type DocumentoDfdViewProps = {
  id: number;
};

export function DocumentoDfdView({ id }: DocumentoDfdViewProps) {
  const suite = getGovSuiteBySlug("documento_dfd");
  if (!suite) {
    return <StatusState kind="error" message="Suite de documento DFD nao configurada." />;
  }
  return <GovDetailView suiteKey={suite.key} id={id} />;
}
