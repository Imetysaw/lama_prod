[![status](https://joss.theoj.org/papers/f91f03787429efa115f1e3aa144254bc/status.svg)](https://joss.theoj.org/papers/f91f03787429efa115f1e3aa144254bc)

# LaMa (Labelling Machine)

![LaMa logo](/frontend/assets/lama_nobg.png)
===

LaMa is a Thematic Labelling web application that can facilitate easier analysis of texts by allowing to add labels to these text artifacts and group the created labels into themes. This tool was developed by a team of nine students for the Final Bachelor Project at the Eindhoven University of Technology.

The tool was created to facilitate collaboration and peer feedback on labelled artifacts. LaMa allows for the user to label text in order to find patterns in qualitative data. Using this tool will allow for an easier, faster, and more structured way for one or more people to label a given text and resolve any conflicts that arise between labels. Additionally, it provides an free and open-source alternative for the commercial tools, such as [Atlas.ti](https://atlasti.com/) and [maxQDA](https://www.maxqda.com/).

This project builds upon the already existing [Labeling Machine tool](https://github.com/muctadir/labeling-machine) by extending it and adding new functionalities, which include but are not limited to a new API and remaking the User Interface (UI).

## Table of Content

1. [Dependencies](#dependencies)
2. [Installation](#installation)
3. [User Manual](#user_manual)
4. [Testing](#testing)
5. [Acknowledgements](#acknowledgements)

## <a name="dependencies"></a>Dependencies

For deployment using docker:

1. [Docker](https://www.docker.com/) ≥ 20.10 (with compose plugin)
2. [Git](https://git-scm.com/) ≥ 2.37.0

For development these are the dependencies/tools without which LaMa may not work:

1. [NodeJS](https://nodejs.org/en/) 16 (Angular 13 does not support newer versions)
2. [AngularCLI](https://angular.io/guide/setup-local) ≥ 13.3.10
3. [Python](https://www.python.org/) ≥ 3.13
4. pip ≥ 22.1.2
5. [Docker](https://www.docker.com/) ≥ 20.10 (with compose plugin)
6. IDE (optional, but recommended for easier development. We recommend [PyCharm](https://www.jetbrains.com/pycharm) for Backend and [VSCode](https://code.visualstudio.com/) for Frontend)

## <a name="installation"></a>Installation

Assuming that you have all the necessary dependencies installed, clone the repository and open a terminal in its root directory. There are two docker setups:

| | Development | Production |
|---|---|---|
| Compose file | `Docker/docker-compose.dev.yml` | `Docker/docker-compose.prod.yml` |
| Configuration | `.env` (committed, insecure defaults) | `.env.prod` (create from `.env.prod.example`, git-ignored) |
| Protocol | HTTP on port 8080 (`HTTP_PORT`) | HTTPS on 443 (Let's Encrypt, renewed automatically), HTTP on 80 redirects |
| Backend | Flask dev server with auto-reload, also published on `127.0.0.1:5000` | gunicorn, only reachable through nginx at `/api` |
| Database / PhpMyAdmin | published on `127.0.0.1` | not published; PhpMyAdmin only with `--profile tools`, on `127.0.0.1` |

In both setups nginx (the `lama-frontend` container) serves the Angular app and proxies `/api` to the backend, so the browser only talks to a single origin.

### Development

```
docker compose --env-file .env -f Docker/docker-compose.dev.yml up --build -d
docker compose --env-file .env -f Docker/docker-compose.dev.yml down
```

LaMa now runs on [localhost:8080](http://localhost:8080). The default login is `admin` / `password`. PhpMyAdmin runs on [localhost:81](http://localhost:81).

### Production (HTTPS)

Requirements: a server with Docker, a DNS name (e.g. `lama.example.org`) whose A/AAAA record points to the server, and **ports 80 and 443 open to the internet** (Let's Encrypt validates the domain over port 80). On SURF Research Cloud, make sure the workspace's security group / firewall allows inbound 80 and 443.

1. Create the production configuration and fill it in. Set `DOMAIN` and `CERTBOT_EMAIL`, and replace every `CHANGE_ME` (generate secrets with `openssl rand -hex 32`). The backend refuses to start while `SECRET_KEY`, `DB_PASSWORD` or `SUPER_PASSWORD` are still `CHANGE_ME`.
```
cp .env.prod.example .env.prod
```
2. Make sure nothing else on the server uses port 80 or 443 (see [Troubleshooting](#troubleshooting)).
3. Start LaMa:
```
docker compose --env-file .env.prod -f Docker/docker-compose.prod.yml up --build -d
```
4. Follow the certificate request with `docker compose --env-file .env.prod -f Docker/docker-compose.prod.yml logs -f lama-certbot`. Until the certificate is issued nginx serves plain HTTP; within a minute after it is issued nginx switches to HTTPS by itself.

How the certificates work:
* The `lama-certbot` container requests the certificate on first start (HTTP-01 challenge via the webroot served by nginx) and retries every 15 minutes if that fails.
* It runs `certbot renew` every 12 hours. Certbot only renews certificates that expire within 30 days.
* nginx reloads itself every 6 hours, so renewed certificates are picked up without a restart.
* Certificates are stored in the `certbotConf` docker volume, so they survive restarts and rebuilds.
* To test the setup without hitting Let's Encrypt's rate limits, set `CERTBOT_STAGING=1` first. Staging certificates are not trusted by browsers. Before switching to real certificates, remove the certificate volumes: `docker compose --env-file .env.prod -f Docker/docker-compose.prod.yml down && docker volume rm lama_certbotConf lama_certbotWww`.

If the server already runs a reverse proxy that terminates TLS (and you cannot or may not stop it, e.g. the nginx that SURF Research Cloud installs on workspaces), run LaMa behind it. Set this in `.env.prod`:
```
NGINX_MODE=http
BIND_ADDRESS=127.0.0.1
HTTP_PORT=8080
HTTPS_PORT=8443
```
and point the existing proxy at `http://127.0.0.1:8080` (with `client_max_body_size 50m;` for artifact uploads). The certbot container then stays idle, and LaMa is only reachable through the existing proxy.

PhpMyAdmin (only if needed): `docker compose --env-file .env.prod -f Docker/docker-compose.prod.yml --profile tools up -d lama-phpmyadmin`, then open an SSH tunnel with `ssh -L 8081:localhost:8081 <server>` and browse to [localhost:8081](http://localhost:8081).

Updating: `git pull`, then run the `up --build -d` command again. Data is kept in the `mysqlData` volume. Back up the database with:
```
docker compose --env-file .env.prod -f Docker/docker-compose.prod.yml exec lama-db sh -c 'mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' > lama-backup.sql
```

### <a name="troubleshooting"></a>Troubleshooting

**`failed to bind host port 0.0.0.0:80/tcp: address already in use`**: another program on the server already listens on port 80 (often a web server installed on the host, e.g. nginx or Apache). Find it with:
```
sudo ss -ltnp 'sport = :80'
sudo ss -ltnp 'sport = :443'
```
Then either stop and disable it, e.g. `sudo systemctl disable --now nginx` (or `apache2`), or, if it has to stay, use the `NGINX_MODE=http` setup described above. If it is an old LaMa container, find it with `docker ps` and stop it. For development you can pick any free port with `HTTP_PORT` in `.env`.

### Setup for development without docker

Database:
1. Open a terminal in the root directory of the repository
2. Start the database with:
```
docker compose --env-file .env -f Docker/docker-compose-db.yml up -d
```
3. Shut down the database with:
```
docker compose --env-file .env -f Docker/docker-compose-db.yml down
```

Frontend:
1. Open a terminal in the frontend directory
2. Run `npm ci` (Angular 13 requires Node 16)
3. Run `npm start` (creates the environment file from `.env` and runs `ng serve`)
4. The frontend server will run on localhost:4200 and talk to the backend on localhost:5000

Backend:
1. Open a terminal in the backend directory
2. On your first time create a virtual environment with `python -m venv venv` (Python 3.13)
3. Activate your virtual environment, `.\venv\Scripts\activate` on Windows or `source venv/bin/activate` on Linux
4. Run `pip install -r requirements-dev.txt`
5. Run the following commands (the `.env` in the root of the repository is loaded automatically):
```
flask db-safe init
flask db migrate
flask db upgrade
flask db-safe add-super-admin
flask run --host=0.0.0.0 --debug
```
6. Run `deactivate` to deactivate the virtual environment

### Environment variables

Development uses the `.env` file in the root of the repository; production uses `.env.prod` (see `.env.prod.example`, which documents every variable). The files are divided into sections:

1) Domain & HTTPS (production only) - `DOMAIN`, `CERTBOT_EMAIL`, `CERTBOT_STAGING`, `NGINX_MODE` (`https` or `http`) and the published ports `HTTP_PORT` / `HTTPS_PORT`.
2) Database - these are all the variables that have anything to do with the database, such as the database port, database login details etc.
3) PhpMyAdmin - the port PhpMyAdmin is published on (on 127.0.0.1 only).
4) LaMa Config - these variables define the superadmin username and password. Please note that a superadmin is created by default who has access to all the projects and their contents. The AUTO_APPROVAL variable determines whether new accounts are approved by default, or must be approved by super admins; it should parse as a boolean.
5) Flask Server - `APP_ENV` (`development` runs the Flask dev server, `production` runs gunicorn), `SECRET_KEY` (signs the login tokens; required in production), `TOKEN_EXPIRY_HOURS`, `GUNICORN_WORKERS` and `CORS_ORIGINS` (origins that may call the API directly; only needed for `ng serve`).
6) Frontend - `API_URL` is the backend URL used by `ng serve`, `PROD_API_URL` the one baked into production builds (`/api`, proxied by nginx).

Secrets are passed to the containers at runtime and are not baked into the docker images.

### Sample Database

With the database running do the following:

1) Go the PMA, which runs on localhost:81 by default in development.
2) In the lama database, check all tables and _drop_ them. You _will_ lose all your data.
3) Go to the import tab, choose the `sample.sql` file found in the root of the repository, and press Go.

The sample database contains one project on the topic of restaurant reviews, and this project already has some labelled artifacts. The three main criteria for reviews are the food, service, and decor. There are two users with the following login details:
- Username: `admin` Password: `password`
- Username: `John Doe` Password: `Testing123`

## <a name="user_manual"></a>User Manual

### Participating in project

Projects are the fundamental building block of the tool, functionalities are on a per project basis. There are 2 ways to participate in a project:

* Create your own project
* Join an existing project

Creating a project can be done through the **Create project** button at the top right of the screen, this opens a menu in which settings of the project can be configured.
![alt text](https://github.com/muctadir/lama/blob/main/images/SS1M.png?raw=true)

To join an existing project the project admin of that project needs to add your account through the **project setting menu** of the project. The project settings menu can be opened through the **setting (gear icon)** in the menu bar on the left after opening the project.

![alt text](https://github.com/muctadir/lama/blob/main/images/SS2M.png?raw=true)

### Uploading artifacts

After participating in a project, for any functionality first artifacts have to be added. Artifacts can be added by navigating to the **Artifact management page**, from the navigation menu on the left after opening the project. On the artifact management page click the **Add artifact** button at the top right, and upload a _.txt_ file containing the artifact(s).

![alt text](https://github.com/muctadir/lama/blob/main/images/SS3M.png?raw=true)

### Labelling an artifact

After having uploaded artifacts it is possible to start labelling them. Navigate using the **navigation menu** on the left to the **labelling page**. An artifact will be shown here. To label an artifact, select labels from the **dropdown menu** below the artifact text.

![alt text](https://github.com/muctadir/lama/blob/main/images/SS4M.png?raw=true)

New labels can be created using the **add label** button above the dropdown menu. The remark text-field can be used to add comments on why a certain label was selected.

![alt text](https://github.com/muctadir/lama/blob/main/images/SS5M.png?raw=true)

_Note: Labels have a label type, this is a way grouping of labels. To label an artifact the user should select a label from each label type. Label types are specified during the project creation, and are not adjustable afterwards._

### Conflict resolution

After different users have labelled an artifact there could be conflict between the labels that have been assigned. Artifacts with different labels appear in the **conflict resolution page**. Here users can modify the labelling given to ensure that there is conformity between the assigned labels. 

![alt text](https://github.com/muctadir/lama/blob/main/images/SS6M.png?raw=true)

Clicking the **resolve conflict** button will resolve the conflict if the labels are consistent.

![alt text](https://github.com/muctadir/lama/blob/main/images/SS7M.png?raw=true)

### Exporting labels

The labelling results of a project can be downloaded from the **Statistics** page with the **Export labels (CSV)** and **Export labels (JSON)** buttons. Project admins get the labellings of every user; other members get only their own. The export has one row per artifact, label type and labeller, with the columns:

`artifact_id`, `artifact_identifier`, `artifact_text`, `parent_artifact_id` (set for artifacts created by splitting), `label_type`, `label`, `label_description`, `themes` (the themes of the label, separated by `; `), `labeller`, `remark`, `labelling_time`.

* **CSV** is meant for spreadsheet programs. It is UTF-8 with a byte order mark so Excel opens it correctly. To protect against [formula injection](https://owasp.org/www-community/attacks/CSV_Injection), cells that start with `=`, `+`, `-` or `@` are prefixed with a `'`.
* **JSON** contains the exact values and is meant for analysis scripts, e.g. `pandas.read_json("lama_project_1_labellings.json")`.

The same data is available from the API at `GET /api/export/labellings?p_id=<project id>&format=csv|json` (send the login token in the `u_id_token` header).

### Advanced features

For a full list of features we refer the reader to the **Software User Manual (SUM)**, below we will briefly describe some of the more important advanced features for common use cases.

* Artifacts can be viewed on the **artifact management page**. Additional info about labels given to artifacts can be seen by clicking on an artifact.
* Segments from an artifact can be transformed into a new artifact, this operation is referred to as **"split"**. Splitting of artifacts is done by highlighting the portion of the artifact to be split on the labelling page, and then clicking the **scissor icon** in the top right.
* The label management page displays all labels in a project, changes can be made to labels, such as editing names, merging labels.
* Themes can be created to provide a logical grouping of labels, allowing for better analysis. Themes are created on the **theme management page**. Labels are assigned to themes on the label management page, or the theme management page.
* Themes can be logically grouped with other themes to create a hierarchical view of the elements within a project.
* Artifacts, labels and themes store change history. This can be inspected by clicking the **clock icon** when viewing the aforementioned elements.
* Various project **statistics** can be viewed on the statistics page. The user can navigate to the statistics page using the navigation menu on the left side of the screen.
* The hierarchy and status of labels and themes can be visualized by clicking the **Theme hierarchy** button on the theme management page. A visualization will be displayed showing how the different elements are related to another, and their current status.

## <a name="testing"></a>Testing

### Frontend testing
1. Navigate to the frontend folder on the terminal
2. To install the required libraries run the command:
```
npm install
```
2. After this command has executed succesfully, run the front-end test cases using the command:

```
ng test
```

### Backend testing

1. Navigate to the backend folder on the terminal
2. To install the required dependencies run the command:
```
pip install -r requirements-dev.txt
```
3. After this command has executed succesfully, run the back-end test cases using the command:
```
pytest -rA
```
(if pytest has not been added to your path, instead run: python -m pytest -rA)

## <a name="citing"></a>Citing this work

Please use the following Bibtex for citing this work.

```
@article{lama2023, 
  author = {Victoria Bogachenkova and Eduardo Costa Martins and Jarl Jansen and Ana-Maria Olteniceanu and Bartjan Henkemans and Chinno Lavin and Linh Nguyen and Thea Bradley and Veerle Fürst and Hossain Muhammad Muctadir and Mark van den Brand and Loek Cleophas and Alexander Serebrenik}, 
  title = {LaMa: a thematic labelling web application}, 
  journal = {Journal of Open Source Software}, 
  doi = {10.21105/joss.05135}, 
  url = {https://doi.org/10.21105/joss.05135}, 
  year = {2023}, 
  publisher = {The Open Journal}, 
  volume = {8},
  number = {85}, 
  pages = {5135} 
} 
```


## <a name="acknowledgements"></a>Acknowledgements

LaMa was developed based on a web application called [Labeling Machine](https://github.com/muctadir/labeling-machine), which is forked from an earlier version of the [Labeling Machine](https://github.com/emadpres/labeling-machine). Development of LaMa was partially funded by NWO (the Dutch national research council) under the NWO AES Perspective program (Digital Twin), project code P18-03 P3. We acknowledge the contribution of the nine bachelor students from [Eindhoven University of Technology, the Netherlands](https://www.tue.nl) V. Bogachenkova, T. Bradley, E.J. Costa Martins, V. Fürst, B. Henkemans, J.L.O. Jansen, L.C. Lavin, L.V. Nguyen, and A. Olteniceanu, who contributed to this project significantly as part of their final project of the bachelors program in computer science.
