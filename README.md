This repository is meant to store the export of the CODES https://xgitlab.cels.anl.gov/codes/codes repository. This export is in JSON format and can be used to import things like issues and merge requests over using the GitHub API.


To use (joint-importer.py) to import a Gitlab JSON export to GitHub via Github's REST v3 API:

1. Generate a GitHub personal access token with the correct permissions to modify the repository you wish to import to.
2. Export it to your command line environment as `GH_TOKEN`
3. Replace the `GH_ONWER` and `GH_REPO` variables with the respective repo owner and name that you wish to import to.
4. Replace the base URL for issues and merge requests from source so that they can be linked in the imported versions.
5. Execute `python3 joint-importer.py` in command line environment.
6. Type `proceed` when prompted to begin import process. Script is purposely slowed down to prevent GitHub abuse detection rate limiting and to ensure that requests are received in correct order.