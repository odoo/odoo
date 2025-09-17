cd C:\Users\felix\Documents\Projet\odoo\odoo17

robocopy . ..\server_config\images\odoo\17\data /mir /XD ./.github

cd ..\server_config\images\odoo\17\data
git add .\*
git commit -m "update project odoo odoo-17" -- .\
git push
