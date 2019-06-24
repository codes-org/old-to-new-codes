from collections import OrderedDict
import json
import requests
import os

all_issues = []

author_id_map = {} # maps user ID numbers to full names
secondary_author_id_map = {} #uses user names instead of full name

issues_base_url = "https://xgitlab.cels.anl.gov/codes/codes/issues/"

GH_OWNER = "codes-org"
GH_REPO = "codes"

print("Loading GitHub Personal Access Token")
GH_TOKEN = os.environ["GH_TOKEN2"] #make sure you export your own github api personal acess token to your command line
print("Success\n")

#Class for comments on issues - called Notes in GitLab land
class Note:
    def __init__(self, author_name=None, timestamp=None, body=None):
        self.author_name = author_name
        self.timestamp = timestamp

        formatted_body = body.replace("#","`#`")
        formatted_body = formatted_body.replace("```text","```")


        self.body = "**%s**:\n\n"%self.author_name + formatted_body

    def __str__(self):
        str_val = ""
        str_val += "%s - (%s): %s\n"%(self.author_name, self.timestamp, self.body)
        
        return str_val

#Class to organize an issue and allow for easy json exporting to GitHub's REST API
class Issue:
    def __init__(self, title=None, orig_author=None, orig_body=None, orig_issue_id=None, created_at=None, updated_at=None, closed_at=None, closed="open"):
        self.title = title + " (Old #%s)"%orig_issue_id
        self.orig_author = orig_author
        self.orig_issue_id = orig_issue_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.closed_at = closed_at
        self.closed = closed
        self.orig_issue_url = issues_base_url + str(orig_issue_id)

        orig_body = str(orig_body)
        formatted_body = orig_body.replace("#","`#`")
        formatted_body = formatted_body.replace("```text","```")

        formatted_body = "Original Issue Author: %s\n Original Issue ID: %s\n Original Issue URL: %s\n______\n"%(orig_author,orig_issue_id,self.orig_issue_url) + formatted_body

        self.body = str(formatted_body)

        self.notes = []

    def add_note(self, note):
        self.notes.append(note)

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

def load_project_file(filename):
    print("Loading Project JSON File...")

    with open(filename, 'r') as f:
        full_json_in = json.load(f)

    print("Success\n")
    return full_json_in

def load_issue_file(filename):
    print("Loading Issues JSON File...")

    with open(filename, "r") as f:
        json_in = json.load(f)['issues']

    print("Success\n")
    return json_in

# issue author names is not stored - but it is stored when they make notes or comments, so this searches for notes and comments to find ID/Author pairs
def find_author_id_pairs(root):
    for key in root:
        if type(root[key]) == list:
            for item in root[key]:
                # print(item)
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



def main():

    #This gets us author names pulled from various actions since the creating author is not kept
    full_json_in = load_project_file("../export/project.json")
    find_author_id_pairs(full_json_in)

    #This 
    json_in = load_issue_file("../export/issues-sample.json")
    issue_list = process_issues(json_in)


    print("Sending to GitHub...")

    for issue in issue_list:
        # print(issue.to_json())
        create_github_issue(issue)
    

if __name__ == "__main__":
    main()