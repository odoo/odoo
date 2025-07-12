document.addEventListener("DOMContentLoaded", function () {
    // Little eye
    document.body.addEventListener("mousedown", function (ev) {
        if (ev.target.classList.contains("o_little_eye")) {
            const closestInputGroup = ev.target.closest(".input-group");
            if (closestInputGroup) {
                const formControl = closestInputGroup.querySelector(".form-control");
                if (formControl) {
                    formControl.type = formControl.type === "text" ? "password" : "text";
                }
            }
        }
    });

    // db modal
    document.body.addEventListener("click", function (ev) {
        if (ev.target.classList.contains("o_database_action")) {
            ev.preventDefault();
            const db = ev.target.getAttribute("data-db");
            const target = ev.target.getAttribute("data-bs-target");
            const modal = Modal.getOrCreateInstance(document.querySelector(target));
            const inputName = modal._element.querySelector("input[name=name]");
            if (inputName) {
                inputName.value = db;
            }
            modal.show();
        }
    });

   document.getElementById('backup_format').addEventListener("change", function (ev) {
            ev.preventDefault();
            const no_filestore_flag = document.getElementById("filestore_div");
            if (no_filestore_flag) {
                if (ev.target.value != "zip") {
                    no_filestore_flag.classList.add("d-none");
                } else {
                    no_filestore_flag.classList.remove("d-none");
                }
            }
    });

    // close modal on submit
    const modals = document.querySelectorAll(".modal");
    for (const modalEl of modals) {
        modalEl.addEventListener("submit", function (ev) {
            const form = ev.target.closest("form");
            if (form && !form.checkValidity?.()) {
                return;
            }
            const modal = Modal.getOrCreateInstance(modalEl);
            modal.hide();
            if (modalEl.classList.contains("o_database_backup")) {
                if (!document.querySelector(".alert-backup-long")) {
                    const listGroup = document.querySelector(".list-group");
                    if (listGroup) {
                        const alert = document.createElement("div");
                        alert.className = "alert alert-info alert-backup-long";
                        alert.textContent =
                            "The backup is on its way; if your database has a lot of data, you may want to go grab a coffee...";
                        listGroup.parentNode.insertBefore(alert, listGroup);
                    }
                }
            }
        });
    }
    // generate a random master password
    // removed l1O0 to avoid confusions
    const charset = "abcdefghijkmnpqrstuvwxyz23456789";
    let password = "";
    for (let i = 0; i < 12; ++i) {
        password += charset.charAt(Math.floor(Math.random() * charset.length));
        if (i === 3 || i === 7) {
            password += "-";
        }
    }
    const masterPwds = document.getElementsByClassName("generated_master_pwd");
    for (const pwdElement of masterPwds) {
        pwdElement.innerText = password;
    }
    const masterPwdInputs = document.querySelectorAll(".generated_master_pwd_input");
    for (const pwdInput of masterPwdInputs) {
        pwdInput.value = password;
        pwdInput.setAttribute("autocomplete", "new-password");
    }
});
