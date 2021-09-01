sudo apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev -y
sudo apt-get install gcc -y
sudo apt-get install g++ -y
sudo apt-get install python3-dev -y
sudo apt-get install python3-pip -y
virtualenv -p python3 venv
source venv/bin/activate
pip3 install -r requirements.txt
