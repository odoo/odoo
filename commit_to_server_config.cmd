cd C:\Users\felix\Documents\Projet\odoo\odoo18

robocopy . ..\..\server_config\images\odoo\17\data /mir /XD ".git" /NP /MT:16

cd ..\server_config\images\odoo\18\data
git add .\*
git commit -m "update project odoo odoo-18" -- .\
git push
