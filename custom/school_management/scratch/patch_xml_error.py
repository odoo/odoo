# -*- coding: utf-8 -*-
with open('static/src/school_management/teacher_dashboard_shell.xml', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''          <!-- LOADING SKELETON -->
          <div t-if="state.isLoading or !state.dashboard" class="d-flex flex-column gap-3" aria-busy="true">'''

replacement = '''          <!-- ERROR ALERT BANNER -->
          <div t-if="state.error" class="alert alert-danger d-flex align-items-center justify-content-between p-3 rounded-3" role="alert">
            <div class="d-flex align-items-center gap-2">
              <i class="fa fa-exclamation-triangle text-danger fs-5" aria-hidden="true"></i>
              <span class="fw-semibold text-danger" t-esc="state.error"/>
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger" t-on-click="() => this.reload()">
              <i class="fa fa-refresh me-1" aria-hidden="true"></i> Retry
            </button>
          </div>

          <!-- LOADING SKELETON -->
          <div t-elif="state.isLoading" class="d-flex flex-column gap-3" aria-busy="true">'''

if target in text:
    new_text = text.replace(target, replacement, 1)
    with open('static/src/school_management/teacher_dashboard_shell.xml', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Updated teacher_dashboard_shell.xml successfully!")
else:
    print("Target not found!")
