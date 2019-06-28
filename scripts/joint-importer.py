import json
import requests
import os
from time import sleep

issues_base_url = "https://xgitlab.cels.anl.gov/codes/codes/issues/" #This is the base URL for old GitLab Issues
mr_base_url = "https://xgitlab.cels.anl.gov/codes/codes/merge_requests/" #This is the base URL for old GitLab MR

GH_OWNER = "codes-org"
GH_REPO = "test-codes"

print("Loading GitHub Personal Access Token")
GH_TOKEN = os.environ["GH_TOKEN"] #make sure you export your own github api personal acess token to your command line
print("Success\n")

#GLOBAL VARIABLES -------------------

author_id_map = {} # maps user ID numbers to full names
secondary_author_id_map = {} #uses user names instead of full name


#CLASSES -------------------------------------------------------------------------------

#Class for comments on issues - called Notes in GitLab land
class Note:
    def __init__(self, author_name=None, timestamp=None, body=None):
        self.author_name = author_name
        self.timestamp = timestamp

        formatted_body = body
        formatted_body = formatted_body.replace("```text","```")

        self.body = "**%s**:\n\n"%self.author_name + formatted_body

    def __str__(self):
        str_val = ""
        str_val += "%s - (%s): %s\n"%(self.author_name, self.timestamp, self.body)
        
        return str_val

    #This is to follow githubs issue comment REST api - actual issues don't use this, but the pull requests do.
    def to_json(self):
        data = {}

        data['body'] = "(%s): %s\n"%(self.timestamp, self.body)
        
        return json.dumps(data)

#Class to organize an issue and allow for easy json exporting to GitHub's REST API
class Issue:
    def __init__(self, title=None, orig_author=None, orig_body=None, orig_issue_id=None, created_at=None, updated_at=None, closed_at=None, closed="open"):
        self.title = title + " (Imported #%s)"%orig_issue_id
        self.orig_author = orig_author
        self.orig_issue_id = orig_issue_id
        self.new_issue_id = None
        self.created_at = created_at
        self.updated_at = updated_at
        self.closed_at = closed_at
        self.closed = closed
        self.orig_issue_url = issues_base_url + str(orig_issue_id)

        formatted_body = str(orig_body)
        # formatted_body = body.replace("#","`#`")
        formatted_body = formatted_body.replace("```text","```")

        formatted_body = "Original Issue Author: %s\nOriginal Issue ID: %s\nOriginal Issue URL: %s\n______\n"%(orig_author,orig_issue_id,self.orig_issue_url) + formatted_body

        self.body = str(formatted_body)

        self.notes = []

    def add_note(self, note):
        self.notes.append(note)

    # Issues utilize github's latest import api and so they don't follow what is actually listed on github's api - eyeroll.
    def to_json(self):
        data = {}

        data['issue'] = {'title': self.title,
                        'body': self.body,
                        'created_at': self.created_at,
                        'closed_at': self.closed_at,
                        'updated_at': self.updated_at,
                        'closed': self.closed}

        if data['issue']['closed_at'] == "None":
            del data['issue']['closed_at']
        if data['issue']['updated_at'] == "None":
            del data['issue']['updated_at']

        comments = []

        for note in self.notes:
            comment = {}
            comment["created_at"] = note.timestamp
            comment["body"] = "%s"%(note.body)

            comments.append(comment)

        data['comments'] = comments

        return json.dumps(data)

    def __str__(self):
        str_val = ""
        str_val += "Title: %s\n"%(self.title)
        str_val += "Author: %s\n"%(self.orig_author)
        str_val += "Original Issue ID: %s\n"%(self.orig_issue_id)
        str_val += "Created At: %s\n"%(self.created_at)
        str_val += "Updated At: %s\n"%(self.updated_at)
        str_val += "Closed At: %s\n"%(self.closed_at)
        str_val += "Closed: %s\n"%(self.closed)
        str_val += "Original Issue URL: %s\n"%(self.orig_issue_url)
        str_val += "\nIssue Body:\n%s\n"%(self.body)
        str_val += "\n\nNotes:\n"

        for note in self.notes:
            str_val += "\t-%s\n"%(str(note))

        return str_val


class Merge_Request:
    def __init__(self, title=None, orig_author=None, orig_body=None, orig_mr_id=None, created_at=None, updated_at=None, state="open", head_branch=None, target_branch=None):
        self.title = title + " (Imported !%s)"%orig_mr_id
        self.head_branch = head_branch
        self.target_branch = target_branch
        self.orig_author = orig_author
        self.orig_mr_id = orig_mr_id
        self.new_issue_id = None
        self.created_at = created_at
        self.updated_at = updated_at
        self.state = state
        self.orig_mr_url = mr_base_url + str(orig_mr_id)

        formatted_body = str(orig_body)
        formatted_body = formatted_body.replace("```text", "```")

        formatted_body = "Original MR Author: %s\nOriginal MR ID: %s\nOriginal MR URL: %s\n______\n"%(orig_author,orig_mr_id,self.orig_mr_url) + formatted_body

        self.body = str(formatted_body)

        self.notes = []

    def add_note(self, note):
        self.notes.append(note)

    # follows github's pull request REST api
    def to_json(self):
        data = {}

        data['title'] = self.title
        data['head'] = self.head_branch
        data['base'] = self.target_branch
        data['body'] = self.body

        return json.dumps(data)

    def __str__(self):
        str_val = ""
        str_val += "Title: %s\n"%(self.title)
        str_val += "Head: %s\n"%(self.head_branch)
        str_val += "Target: %s\n"%(self.target_branch)
        str_val += "Created At: %s\n"%(self.created_at)
        str_val += "Updated At: %s\n"%(self.updated_at)
        str_val += "State: %s\n"%(self.state)
        str_val += "\nMR Body:\n%s\n"%(self.body)
        str_val += "\n\nNotes:\n"

        for note in self.notes:
            str_val += "\t-%s\n"%(str(note))

        return str_val

#METHODS --------------------------------------------------------------------

def load_project_file(filename):
    print("Loading Project JSON File...")

    with open(filename, 'r') as f:
        full_json_in = json.load(f)

    print("Success\n")
    return full_json_in

def load_data_file(filename, datatype):
    print("Loading %s JSON File..."%datatype)

    with open(filename, "r") as f:
        json_in = json.load(f)[datatype]

    print("Success\n")
    return json_in

# issue author names are not stored in the export - but it is stored when they make notes or comments, so this searches for notes and comments to find ID/Author pairs
# as a backup it also looks at the project members area but this doesn't have full names, nor does it have a history of anyone who has ever been a member  - just who is currently one.
def find_author_id_pairs(root):
    for key in root:
        if type(root[key]) == list:
            for item in root[key]:
                if type(item) is dict:
                    if "notes" in item:
                        for note in item["notes"]:
                            author_id = note["author_id"]
                            author_name = note["author"]["name"]

                            if author_id not in author_id_map:
                                author_id_map[author_id] = author_name
                    if "user" in item:
                        user_id = item['user']['id']
                        user_name = item['user']['username']

                        if user_id not in secondary_author_id_map:
                            secondary_author_id_map[user_id] = user_name


#create an issue object from a single issue from the json file
def parse_issue(issue_raw):
    #Issue Title
    issue_title = issue_raw['title']
    
    #Issue Author
    issue_author_id = issue_raw['author_id']
    if (issue_author_id in author_id_map):
        issue_author = author_id_map[issue_author_id]
    elif (issue_author_id in secondary_author_id_map):
        issue_author = secondary_author_id_map[issue_author_id]
    else:
        issue_author = "Not recorded"

    #Issue Body
    issue_body = issue_raw['description']

    #Original Issue ID number
    orig_issue_id = str(issue_raw['iid'])

    #Timestamps
    created_at = str(issue_raw['created_at'])
    updated_at = str(issue_raw['updated_at'])
    closed_at = str(issue_raw['closed_at']) #weirdly sometimes the issue can be closed without this being set :\

    #is_closed set
    closed_status = str(issue_raw['state'])

    if closed_status == "closed":
        is_closed = True
    else:
        is_closed = False

    #Create the issue object
    new_issue = Issue(title=issue_title, orig_author=issue_author, orig_body=issue_body, orig_issue_id=orig_issue_id, created_at=created_at, updated_at=updated_at, closed_at=closed_at, closed=is_closed)
    
    #populate its notes
    for note_json in issue_raw['notes']:
        note_author = note_json['author']['name']
        note_timestamp = note_json['updated_at']
        note_body = note_json['note']

        new_note = Note(note_author, note_timestamp, note_body)

        new_issue.add_note(new_note)
    
    
    return new_issue

#Parse all isues from the issues specific json file
def process_issues(json_in):
    print("Processing Issues...")
    
    issue_list = []

    for issue_raw in json_in:
        new_issue = parse_issue(issue_raw)
        issue_list.append(new_issue)

    print("Processed %d Issues\n"%len(issue_list))
    return issue_list


def parse_mr(mr_raw):
    mr_title = mr_raw['title']

    head_branch = mr_raw['source_branch']
    target_branch = mr_raw['target_branch']


    mr_author_id = mr_raw['author_id']
    if (mr_author_id in author_id_map):
        mr_author = author_id_map[mr_author_id]
    elif (mr_author_id in secondary_author_id_map):
        mr_author = secondary_author_id_map[mr_author_id]
    else:
        mr_author = "Not Recorded - See Original Link"

    #merge body
    mr_body = mr_raw['description']

    #original MR id number (gitlab numbering)
    orig_mr_id = str(mr_raw['iid'])

    #Timestamps
    created_at = str(mr_raw['created_at'])
    updated_at = str(mr_raw['updated_at'])

    #status
    state = str(mr_raw['state'])
    if state == "opened":
        state = "open"

    #create new MR object
    new_mr = Merge_Request(title=mr_title, orig_author=mr_author,orig_body=mr_body, orig_mr_id=orig_mr_id, created_at=created_at, updated_at=updated_at, state=state, head_branch=head_branch, target_branch=target_branch)

    for note_json in mr_raw['notes']:
        note_author = note_json['author']['name']
        note_timestamp = note_json['updated_at']
        note_body = note_json['note']

        new_note = Note(note_author, note_timestamp, note_body)

        new_mr.add_note(new_note)

    return new_mr

#Parse all MRs from MR specific json file
def process_merge_requests(json_in):
    print("Processing MRs...")
    
    mr_list = []

    for mr_raw in json_in:
        new_mr = parse_mr(mr_raw)
        mr_list.append(new_mr)

    print("Processed %d MRs\n"%len(mr_list))
    return mr_list

def create_github_issue(issue_obj):
    #issue import URL
    url = 'https://api.github.com/repos/%s/%s/import/issues' % (GH_OWNER, GH_REPO)

    #Headers - required to use the API per GitHub's requirements
    headers = {
        "Authorization": "token %s" % GH_TOKEN,
        "Accept": "application/vnd.github.golden-comet-preview+json"
    }

    #Payload
    data = issue_obj.to_json()

    #Add the issue to our repository
    response = requests.request("POST", url, data=data, headers=headers)
    if response.status_code == 202:
        print('Successfully created Issue "%s"' % issue_obj.title)
    else:
        print('Could not create Issue "%s"' % issue_obj.title)
        print('Response:', response.content)


def create_github_pull_request(mr_object):

    url = 'https://api.github.com/repos/%s/%s/pulls' % (GH_OWNER, GH_REPO)

    headers = {
        "Authorization": "token %s" % GH_TOKEN,
        "Accept": "application/vnd.github.sailor-v-preview+json"
    }

    data = mr_object.to_json()

    response = requests.request("POST", url, data=data, headers=headers)
    if response.status_code == 201:
        print('Successfully created MR "%s"' % mr_object.title)
        json_response = json.loads(response.content)
        mr_object.new_issue_id = json_response['number'] #set the new issue ID so we can know where to post comments
    else:
        print('Could not create MR "%s"' % mr_object.title)
        print('Response:', response, response.content)




def add_github_pull_request_comments(mr_object):
    new_pr_id = mr_object.new_issue_id

    url = 'https://api.github.com/repos/%s/%s/issues/%s/comments' % (GH_OWNER, GH_REPO, str(new_pr_id))

    headers = {
        "Authorization": "token %s" % GH_TOKEN,
        "Accept": "application/vnd.github.sailor-v-preview+json"
    }

    sorted_notes = sorted(mr_object.notes, key=lambda x: str(x.timestamp), reverse=False)

    for note in sorted_notes:
        data = note.to_json()
        response = requests.request("POST", url, data=data, headers=headers)

        if response.status_code == 201:
            print("Successfully added comment to %d"%(new_pr_id))
        else:
            print("Could not add comment to %d"%(new_pr_id))
            print('Response:', response,response.content)


def main():

    #This gets us author names pulled from various actions since the creating author is not kept
    full_json_in = load_project_file("../export/project.json")
    find_author_id_pairs(full_json_in)

    #load issues file
    issue_json_in = load_data_file("../export/issues.json","issues")
    issue_list = process_issues(issue_json_in)

    #load merge requests file
    mr_json_in = load_data_file("../export/merges.json","merge_requests")
    mr_list = process_merge_requests(mr_json_in)

    #sort them by their original IDs
    sorted_issue_list = sorted(issue_list, key=lambda x: int(x.orig_issue_id), reverse=False)
    sorted_mr_list = sorted(mr_list, key=lambda x: int(x.orig_mr_id), reverse=False)

    #Simple safety check to prevent someone from doing something without knowing what they were doing
    response = input('This will, without further confirmation and irreversibly, import all loaded issues, merge requests, and comments to the specified GitHub repo (%s/%s). To continue: type "proceed"\n'%(GH_OWNER,GH_REPO))

    if response == "proceed":
        print("Sending to GitHub...")

        print("Sending Issues...")
        for issue in sorted_issue_list:
            create_github_issue(issue)
            sleep(5) #allow github to process to avoid out of order issues and rate-abuse-monitoring

        print("Sending Pull Requests...")
        for mr in sorted_mr_list:
            if mr.state is "open":
                create_github_pull_request(mr)
                sleep(3)  #allow github to process to avoid out of order issues and rate-abuse-monitoring
        
        print("Posting comments to valid pull requests...")
        for mr in sorted_mr_list:
            if mr.state is "open":
                if mr.new_issue_id is not None:
                    add_github_pull_request_comments(mr)
                    sleep(3)  #allow github to process to avoid out of order issues and rate-abuse-monitoring


    else:
        print('Response: "proceed" not found. Cancelling...')
    

if __name__ == "__main__":
    main()

