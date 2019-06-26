import json
import requests
import os
from time import sleep


author_id_map = {} # maps user ID numbers to full names
secondary_author_id_map = {} #uses user names instead of full name

mr_base_url = "https://xgitlab.cels.anl.gov/codes/codes/merge_requests/" #This is the base URL for old GitLab Issues

GH_OWNER = "codes-org"
GH_REPO = "test-codes"

print("Loading GitHub Personal Access Token")
GH_TOKEN = os.environ["GH_TOKEN"] #make sure you export your own github api personal acess token to your command line
print("Success\n")


#Class for comments on issues - called Notes in GitLab land
class Note:
    def __init__(self, author_name=None, timestamp=None, body=None):
        self.author_name = author_name
        self.timestamp = timestamp

        formatted_body = body
        # formatted_body = body.replace("#","`#`")
        formatted_body = formatted_body.replace("```text","```")


        self.body = "**%s**:\n\n"%self.author_name + formatted_body

    def __str__(self):
        str_val = ""
        str_val += "%s - (%s): %s\n"%(self.author_name, self.timestamp, self.body)
        
        return str_val


class Merge_Request:
    def __init__(self, title=None, orig_author=None, orig_body=None, orig_mr_id=None, created_at=None, updated_at=None, state="open", head_branch=None, target_branch=None):
        self.title = title + " (Imported !%s)"%orig_mr_id
        self.head_branch = head_branch
        self.target_branch = target_branch
        self.orig_author = orig_author
        self.orig_mr_id = orig_mr_id
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

    def to_json(self):
        data = {}

        data['title'] = self.title
        data['head'] = self.head_branch
        data['base'] = self.target_branch
        data['body'] = self.body
        data['draft'] = True

        # data['pull_request'] = {'title': self.title,
        #                 'head': self.head_branch,
        #                 'base': self.target_branch,
        #                 'body': self.body,
        #                 'created_at': self.created_at,
        #                 'updated_at': self.updated_at,
        #                 'status': self.state}

        # if data['pull_request']['updated_at'] == "None":
        #     del data['issue']['updated_at']

        # comments = []

        # for note in self.notes:
        #     comment = {}
        #     comment["created_at"] = note.timestamp
        #     comment["body"] = "%s"%(note.body)

        #     comments.append(comment)

        # data['comments'] = comments

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


def load_project_file(filename):
    print("Loading Project JSON File...")

    with open(filename, 'r') as f:
        full_json_in = json.load(f)

    print("Success\n")
    return full_json_in

def load_issue_file(filename):
    print("Loading Issues JSON File...")

    with open(filename, "r") as f:
        json_in = json.load(f)['merge_requests']

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

def create_github_pull_request(mr_object):

    url = 'https://api.github.com/repos/%s/%s/pulls' % (GH_OWNER, GH_REPO)

    headers = {
        "Authorization": "token %s" % GH_TOKEN,
        "Accept": "application/vnd.github.sailor-v-preview+json"
    }

    data = mr_object.to_json()

    # print(data)

    response = requests.request("POST", url, data=data, headers=headers)
    if response.status_code == 201:
        print('Successfully created MR "%s"' % mr_object.title)
    else:
        print('Could not create MR "%s"' % mr_object.title)
        print('Response:', response, response.content)

def main():

    #This gets us author names pulled from various actions since the creating author is not kept
    full_json_in = load_project_file("../export/project.json")
    find_author_id_pairs(full_json_in)

    #This 
    json_in = load_issue_file("../export/merges-sample.json")
    mr_list = process_merge_requests(json_in)


    for mr in mr_list:
        # if mr.state is "open":
            # print(mr)
        create_github_pull_request(mr)
        sleep(1)

    # newlist = sorted(issue_list, key=lambda x: int(x.orig_issue_id), reverse=False)

    #Simple safety check to prevent someone from doing something without knowing what they were doing
    # response = input('This will, without further confirmation and irreversibly, import all loaded issues to the specified GitHub repo (%s/%s). To continue: type "proceed"\n'%(GH_OWNER,GH_REPO))

    # if response == "proceed":
    #     print("Sending to GitHub...")

    #     for issue in newlist:
    #         # print(issue.to_json())
    #         # print(issue.orig_issue_id)
    #         create_github_issue(issue)
    #         sleep(5)
    # else:
    #     print('Response: "proceed" not found. Cancelling...')
    

if __name__ == "__main__":
    main()

