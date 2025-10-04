cd C:\Users\felix\Documents\Projet\odoo\odoo17

robocopy .\odoo ..\..\server_config\images\odoo\17\data /mir /XD ".git" /NP /MT:16
robocopy .\ ..\..\server_config\images\odoo\17 requirements.txt

cd ..\..\server_config\images\odoo\17\data
git add .\*
git add .\..\requirements.txt
git commit -m "update project odoo odoo-17" -- .\..\
git push

