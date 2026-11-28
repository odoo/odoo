with open('custom/school_management/static/src/school_management/dashboard_shell.xml', 'r', encoding='utf-8') as f:
    c = f.read()

target = """            <!-- B. ROLE-SPECIFIC FALLBACK (Dean, HOD, Teacher) -->
            <t t-else="">
              <section class="o_kpi_summary_section" aria-label="Key Performance Metrics">
                <div class="row g-3">"""

replacement = """            <!-- B. ROLE-SPECIFIC FALLBACK (Dean, HOD, Teacher) -->
            <t t-else="">
              <section class="o_kpi_summary_section" aria-label="Key Performance Metrics">
                <div t-if="this.state.dashboard?.user_role === 'teacher'" class="d-flex flex-wrap align-items-center justify-content-between p-3 mb-3 bg-white border rounded-3 shadow-2xs">
                  <div>
                    <h4 class="h6 mb-1 text-dark fw-bold">
                      <i class="fa fa-graduation-cap me-2 text-primary"/>Faculty &amp; Teaching Workspace
                    </h4>
                    <p class="text-muted small mb-0">
                      Manage course schedules, student advisees, grade exam submissions, and track official marksheet analytics.
                    </p>
                  </div>
                  <div class="d-flex gap-2">
                    <button type="button" class="btn btn-primary btn-sm" t-on-click="() => this.openTeacherWorkspace()">
                      <i class="fa fa-th-large me-1"/>Open Teacher Dashboard
                    </button>
                    <button type="button" class="btn btn-outline-success btn-sm" t-on-click="() => this.openSpreadsheetAnalytics()">
                      <i class="fa fa-table me-1"/>Academic &amp; Student Analytics
                    </button>
                  </div>
                </div>
                <div class="row g-3">"""

assert target in c, 'target not found'
c = c.replace(target, replacement, 1)

with open('custom/school_management/static/src/school_management/dashboard_shell.xml', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated dashboard_shell.xml successfully!')
