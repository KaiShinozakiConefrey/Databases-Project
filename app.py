from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify
import psycopg2
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(32))

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

# Home page
@app.route('/')
def index():
    a_id = session.get('a_id', -1)
    user = ""
    workspaces = None
    invitations = None
    if a_id != -1:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT nickname FROM Account WHERE a_id = %s', (a_id,))
        user = cur.fetchone()[0]
        if user == "" or user is None:
            cur.execute('SELECT username FROM Account WHERE a_id = %s', (a_id,))
            user = cur.fetchone()[0]

        #Find invitations
        cur.execute(
            'SELECT w.w_id, w.name, w.description, a.nickname, wi.timestamp, wi.inviter_id ' \
            'FROM workspace_invitation wi JOIN workspace w ON wi.w_id = w.w_id '\
            'JOIN Account a ON wi.inviter_id = a.a_id ' \
            'WHERE wi.invitee_id = %s AND wi.status = %s', (a_id, 'pending')
        )
        invitations = cur.fetchall()

        #Find workspaces
        cur.execute(
            'SELECT w.w_id, w.name, w.description ' \
            'FROM workspace_member wm JOIN workspace w ON wm.w_id = w.w_id ' \
            'WHERE wm.a_id = %s', (a_id,)
        )
        workspaces = cur.fetchall()

        cur.close()
        conn.close()

    return render_template('index.html', user = user, workspaces = workspaces, invitations = invitations)

# Log out
@app.route('/logout')
def logout():
    session.pop('a_id', None)
    return redirect(url_for('index'))

# Auth page (login + create account)
@app.route('/auth')
def auth():
    return render_template('auth.html')

# Log in data submission
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email'].lower()
    password = request.form['password']
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT a_id, password FROM Account WHERE email_address = %s', (email,))
    account = cur.fetchone()
    cur.close()
    conn.close()
    if account and check_password_hash(account[1], password):
        account = (account[0],)
    else:
        account = None
    if account:
        session['a_id'] = account[0]
        return redirect(url_for('index'))
    else:
        flash("Invalid email or password", "error")
        return redirect(url_for('auth'))

# Create account data submission
@app.route('/create_account', methods=['POST'])
def create_account():
    email = request.form['email'].lower()
    username = request.form['username']
    nickname = request.form['nickname']
    password = request.form['password']
    conn = get_db()
    cur = conn.cursor()

    # Chec k if it already exists
    cur.execute('SELECT 1 FROM Account WHERE email_address = %s', (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        flash("Email already in use", "error")
        return redirect(url_for('auth'))
    
    try:
        cur.execute('INSERT INTO Account (email_address, username, nickname, password) VALUES (%s, %s, %s, %s) RETURNING a_id',
                    (email, username, nickname, generate_password_hash(password)))
        account = cur.fetchone()
        conn.commit()

    except(Exception):
        cur.close()
        conn.close()
        flash("Error creating account", "error")
        return redirect(url_for('auth'))

    cur.close()
    conn.close()
    if account:
        session['a_id'] = account[0]
        return redirect(url_for('index'))
    else:
        flash("Failed to create account", "error")
        return redirect(url_for('auth'))

# Create a workspace data submission
@app.route('/create_workspace', methods=['POST'])
def create_workspace():
    workspace_name = request.form['workspace_name']
    description = request.form['description']
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO Workspace (name, description) VALUES (%s, %s) RETURNING w_id',
                (workspace_name, description))
    workspace = cur.fetchone()
    if workspace:
        cur.execute('INSERT INTO workspace_member (w_id, a_id, role) VALUES (%s, %s, %s)',
                    (workspace[0], session['a_id'], 'admin'))
    cur.close()
    conn.commit()
    conn.close()
    if workspace:
        session['w_id'] = workspace[0]
        return redirect(url_for('index'))
    else:
        return redirect(url_for('create_workspace_page'), error = "Failed to create workspace")

@app.route('/workspace', methods=['GET'])
def workspace():
    a_id = session.get('a_id', -1)
    w_id = request.args.get('w_id')
    session['w_id'] = w_id

    conn = get_db()
    cur = conn.cursor()

    #Get workspace name
    cur.execute(
        'SELECT name FROM Workspace WHERE w_id = %s', (w_id,)
    )
    workspace = cur.fetchone()[0]

    #Get list of workspace members
    cur.execute(
        'SELECT a.a_id, wm.role, a.username, a.nickname ' \
        'FROM workspace_member wm JOIN Account a ON wm.a_id = a.a_id ' \
        'WHERE wm.w_id = %s' \
        'ORDER BY wm.role', (w_id,)
    )
    members = cur.fetchall()

    #Get list of channels the user is in

    cur.execute(
        'SELECT c.c_id, c.channel_name, c.channel_description ' \
        'FROM channel_member cm JOIN channel c ON cm.c_id = c.c_id ' \
        'WHERE cm.a_id = %s AND c.w_id = %s', (a_id, w_id)
    )
    channels = cur.fetchall()

    #Get list of public channels in the workspace

    cur.execute(
        'SELECT c.c_id, c.channel_name, c.channel_description ' \
        'FROM channel c JOIN workspace w on c.w_id = w.w_id ' \
        'WHERE c.type = %s AND w.w_id = %s ' \
        'EXCEPT ' \
        'SELECT c.c_id, c.channel_name, c.channel_description ' \
        'FROM channel_member cm JOIN channel c ON cm.c_id = c.c_id ' \
        'WHERE cm.a_id = %s AND c.w_id = %s', ('public', w_id, a_id, w_id)
    )
    public_channels = cur.fetchall()

    #Get list of public channels in the workspace

    #Get role
    cur.execute(
        'SELECT role ' \
        'FROM workspace_member ' \
        'WHERE w_id = %s AND a_id = %s', (w_id, a_id)
    )
    role = cur.fetchone()

    private_channels = []

    if role and role[0] != 'member':
        cur.execute(
            'SELECT c.c_id, c.channel_name, c.channel_description ' \
            'FROM channel c JOIN workspace w on c.w_id = w.w_id ' \
            'WHERE c.type = %s AND w.w_id = %s ' \
            'EXCEPT ' \
            'SELECT c.c_id, c.channel_name, c.channel_description ' \
            'FROM channel_member cm JOIN channel c ON cm.c_id = c.c_id ' \
            'WHERE cm.a_id = %s AND c.w_id = %s', ('private', w_id, a_id, w_id)
        )
        private_channels = cur.fetchall()

    #Find invitations
    cur.execute(
        'SELECT c.c_id, c.channel_name, c.channel_description, a.nickname, ci.timestamp, ci.inviter_id ' \
        'FROM channel_invitation ci JOIN channel c ON ci.c_id = c.c_id '\
        'JOIN Account a ON ci.inviter_id = a.a_id ' \
        'WHERE ci.invitee_id = %s AND ci.status = %s AND c.w_id = %s', (a_id, 'pending', w_id)
    )
    invitations = cur.fetchall()
    
    cur.close()
    conn.close()

    return render_template('workspace.html', 
                           a_id=a_id,
                           w_id=w_id, 
                           members = members, 
                           workspace = workspace, 
                           channels = channels,
                           public_channels = public_channels,
                           private_channels = private_channels,
                           role = role[0],
                           invitations = invitations)

@app.route('/invite_to_workspace', methods=['POST'])
def invite_to_workspace():
    a_id = session.get('a_id', -1)
    w_id = session.get('w_id', -1)

    email = request.form['email'].lower()
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT a_id FROM Account WHERE email_address = %s', (email,))
    invited_user = cur.fetchone()
    
    # Check if user exists
    if not invited_user:
        cur.close()
        conn.commit()
        conn.close()
        flash("User not found", "error")
        return redirect(url_for('workspace', w_id=w_id))
    
    invited_user_id = invited_user[0]

    # Check if the user is attempting to invite themself
    if a_id == invited_user_id:
        cur.close()
        conn.commit()
        conn.close()
        flash("You cannot invite yourself", "error")
        return redirect(url_for('workspace', w_id=w_id))

    # Check if member is already in the workspace
    cur.execute(
        'SELECT a.a_id ' \
        'FROM workspace_member wm JOIN Account a ON wm.a_id = a.a_id ' \
        'WHERE wm.w_id = %s ' \
        'ORDER BY wm.role', (w_id,)
    )
    members = cur.fetchall()
    member_ids = [member[0] for member in members]

    if invited_user_id in member_ids:
        cur.close()
        conn.commit()
        conn.close()
        flash("User is already a member of the workspace", "error")
        return redirect(url_for('workspace', w_id=w_id))

    # Check if the user has already been invited
    cur.execute('SELECT invitee_id, status ' \
                'FROM Workspace_Invitation ' \
                'WHERE inviter_id = %s AND invitee_id = %s', (a_id, invited_user[0]))
    existing_invitation = cur.fetchone()
    if existing_invitation:
        # Check if the invite is still pending, and if so cancel
        if existing_invitation[1] == 'pending':
            cur.close()
            conn.commit()
            conn.close()
            flash("User already has a pending invite to the workspace", "error")
            return redirect(url_for('workspace', w_id=w_id))

        # Check if the invite has been declined, and if so update it
        if existing_invitation[1] == 'declined':
            cur.execute('UPDATE Workspace_Invitation ' \
                'SET status = %s ' \
                'WHERE inviter_id = %s AND invitee_id = %s', ('pending', a_id, invited_user[0]))
            cur.close()
            conn.commit()
            conn.close()
            flash("Invite sent!", "success")
            return redirect(url_for('workspace', w_id=w_id))

    

    cur.execute('INSERT INTO workspace_invitation (inviter_id, invitee_id, w_id, status) VALUES (%s, %s, %s, %s)',
                (a_id, invited_user_id, w_id, 'pending'))
    cur.close()
    conn.commit()
    conn.close()
    flash("Invite sent!", "success")
    return redirect(url_for('workspace', w_id=w_id))

@app.route('/accept_workspace_invitation')
def accept_workspace_invitation():
    invitee_id = session.get('a_id', -1)
    w_id = request.args.get('w_id', -1)

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        'SELECT status FROM Workspace_Invitation '
        'WHERE invitee_id = %s AND w_id = %s FOR UPDATE',
        (invitee_id, w_id)
    )
    inv = cur.fetchone()
    if not inv or inv[0] != 'pending':
        conn.rollback()
        cur.close()
        conn.close()
        return redirect(url_for('index'))

    cur.execute(
        'UPDATE Workspace_Invitation SET status = %s '
        'WHERE invitee_id = %s AND w_id = %s',
        ('accepted', invitee_id, w_id)
    )
    cur.execute(
        'INSERT INTO workspace_member (w_id, a_id, role) VALUES (%s, %s, %s)',
        (w_id, invitee_id, 'member')
    )

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('workspace', w_id=w_id))

@app.route('/reject_workspace_invitation')
def reject_workspace_invitation():
    inviter_id = request.args.get('inviter_id', -1)
    invitee_id = session.get('a_id', -1)
    w_id = session.get('w_id', -1)

    conn = get_db()
    cur = conn.cursor()

    # Update the invitation status to accepted
    cur.execute('UPDATE Workspace_Invitation '
                'SET status = %s '
                'WHERE invitee_id = %s AND w_id = %s AND inviter_id = %s', 
                ('declined', invitee_id, w_id, inviter_id))
    
    cur.close()
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/make_co_admin', methods = ["POST"])
def make_co_admin():
    a_id = request.form['a_id']
    w_id = session.get('w_id')

    conn = get_db()
    cur = conn.cursor()

    cur.execute('UPDATE workspace_member '
                'SET role = %s '
                'WHERE a_id = %s AND w_id = %s', 
                ('co_admin', a_id, w_id))

    cur.close()
    conn.commit()
    conn.close()
    return redirect(url_for('workspace', w_id=w_id))

@app.route('/create_channel', methods = ['POST'])
def create_channel():
    channel_name = request.form['channel_name']
    channel_description = request.form['channel_description']
    channel_type = request.form['type']
    w_id = session.get('w_id')

    #Insert channel into database and add creator as member of channel
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO Channel (w_id, creator_id, channel_name, channel_description, type) VALUES (%s, %s, %s, %s, %s) RETURNING c_id',
                (w_id, session['a_id'], channel_name, channel_description, channel_type))
    channel = cur.fetchone()
    if channel:
        cur.execute('INSERT INTO channel_member (c_id, a_id) VALUES (%s, %s)',
                    (channel[0], session['a_id']))
    cur.close()
    conn.commit()
    conn.close()

    if channel:
        return redirect(url_for('workspace', w_id=w_id))
    else:
        return redirect(url_for('workspace', w_id=w_id), error = "Failed to create channel")

@app.route('/join_channel')
def join_channel():
    a_id = session.get('a_id', -1)
    w_id = session.get('w_id', -1)
    c_id = request.args.get('c_id')

    conn = get_db()
    cur = conn.cursor()

    # Add the user to the workspace members
    cur.execute('INSERT INTO channel_member (c_id, a_id) VALUES (%s, %s)',
                (c_id, a_id))
    
    # Update any invitation status to accepted
    cur.execute('UPDATE Channel_Invitation '
                'SET status = %s '
                'WHERE invitee_id = %s AND c_id = %s', 
                ('accepted', a_id, c_id))
    
    cur.close()
    conn.commit()
    conn.close()
    return redirect(url_for('workspace', w_id=w_id))

@app.route('/channel', methods=['GET'])
def channel():
    a_id = session.get('a_id', -1)
    w_id = request.args.get('w_id')
    c_id = request.args.get('c_id')
    session['w_id'] = w_id
    session['c_id'] = c_id

    conn = get_db()
    cur = conn.cursor()

    #Get workspace name
    cur.execute(
        'SELECT name FROM Workspace WHERE w_id = %s', (w_id,)
    )
    workspace = cur.fetchone()[0]

    #Get channel name
    cur.execute(
        'SELECT channel_name FROM Channel WHERE c_id = %s', (c_id,)
    )
    channel = cur.fetchone()[0]

    #Get list of Channel members
    cur.execute(
        'SELECT a.a_id, a.username, a.nickname ' \
        'FROM channel_member cm JOIN Account a ON cm.a_id = a.a_id ' \
        'WHERE cm.c_id = %s', (c_id,)
    )
    members = cur.fetchall()

    #Get messages in channel
    cur.execute(
        'SELECT m.m_id, m.content, m.timestamp, a.username, a.nickname '\
        'FROM message m JOIN Account a ON m.sender_id = a.a_id '\
        'WHERE m.c_id = %s '\
        'ORDER BY m.timestamp', (c_id,)
    )
    messages = cur.fetchall()

    #Check if user is owner of channel
    cur.execute(
        'SELECT creator_id FROM Channel WHERE c_id = %s', (c_id,)
    )
    creator_id = cur.fetchone()
    if creator_id:
        owner = (creator_id[0])

    #Check if channel is at capacity
    at_capacity = False
    cur.execute(
        'SELECT type FROM Channel WHERE c_id = %s', (c_id,)
    )
    channel_type = cur.fetchone()
    if channel_type[0] == 'direct':
        cur.execute(
            'SELECT 1 FROM Channel_Invitation WHERE c_id = %s LIMIT 1', (c_id,)
        )
        if cur.fetchone():
            at_capacity = True

    cur.close()
    conn.close()

    return render_template('channel.html', 
                           members = members, 
                           workspace = workspace, 
                           channel = channel, 
                           messages = messages,
                           owner = owner,
                           at_capacity = at_capacity)

@app.route('/invite_to_channel', methods=['POST'])
def invite_to_channel():
    a_id = session.get('a_id', -1)
    w_id = session.get('w_id', -1)
    c_id = session.get('c_id', -1)

    email = request.form['email'].lower()
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT a_id FROM Account WHERE email_address = %s', (email,))
    invited_user = cur.fetchone()
    
    # Check if user exists
    if not invited_user:
        cur.close()
        conn.commit()
        conn.close()
        flash("User not found", "error")
        return redirect(url_for('channel', w_id=w_id))
    
    invited_user_id = invited_user[0]

    # Check if the user is attempting to invite themself
    if a_id == invited_user_id:
        cur.close()
        conn.commit()
        conn.close()
        flash("You cannot invite yourself", "error")
        return redirect(url_for('channel', w_id=w_id, c_id=c_id))
    
    # Check if user is in the workspace
    cur.execute(
        'SELECT a.a_id '\
        'FROM workspace_member wm JOIN Account a ON wm.a_id = a.a_id '\
        'WHERE wm.w_id = %s', (w_id,)
    )
    workspace_members = cur.fetchall()
    workspace_member_ids = [member[0] for member in workspace_members]  
    if invited_user_id not in workspace_member_ids:
        cur.close()
        conn.commit()
        conn.close()
        flash("User is not a member of the workspace", "error")
        return redirect(url_for('channel', w_id=w_id, c_id=c_id))
    
    # Check if member is already in the channel
    cur.execute(
        'SELECT a.a_id ' \
        'FROM channel_member cm JOIN Account a ON cm.a_id = a.a_id ' \
        'WHERE cm.c_id = %s;', (c_id,)
    )
    members = cur.fetchall()
    member_ids = [member[0] for member in members]

    if invited_user_id in member_ids:
        cur.close()
        conn.commit()
        conn.close()
        flash("User is already a member of the channel", "error")
        return redirect(url_for('channel', w_id=w_id, c_id=c_id))

    # Check if the user has already been invited
    cur.execute('SELECT invitee_id, status ' \
                'FROM Channel_Invitation ' \
                'WHERE inviter_id = %s AND invitee_id = %s', (a_id, invited_user[0]))
    
    existing_invitation = cur.fetchone()
    if existing_invitation:
        # Check if the invite is still pending, and if so cancel
        if existing_invitation[1] == 'pending':
            cur.close()
            conn.commit()
            conn.close()
            flash("User already has a pending invite to the channel", "error")
            return redirect(url_for('channel', w_id=w_id, c_id=c_id))

        # Check if the invite has been decline, and if so update it
        if existing_invitation[1] == 'declined':
            cur.execute('UPDATE Channel_Invitation ' \
                'SET status = %s ' \
                'WHERE inviter_id = %s AND invitee_id = %s', ('pending', a_id, invited_user[0]))
            cur.close()
            conn.commit()
            conn.close()
            flash("Invite sent!", "success")
            return redirect(url_for('channel', w_id=w_id, c_id=c_id))

    

    cur.execute('INSERT INTO Channel_Invitation (inviter_id, invitee_id, c_id, status) VALUES (%s, %s, %s, %s)',
                (a_id, invited_user_id, c_id, 'pending'))
    cur.close()
    conn.commit()
    conn.close()

    flash("Invite sent!", "success")
    return redirect(url_for('channel', w_id=w_id, c_id=c_id))

@app.route('/accept_channel_invitation')
def accept_channel_invitation():
    invitee_id = session.get('a_id', -1)
    w_id = request.args.get('w_id', -1)
    c_id = request.args.get('c_id', -1)

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        'SELECT status FROM Channel_Invitation '
        'WHERE invitee_id = %s AND c_id = %s FOR UPDATE',
        (invitee_id, c_id)
    )
    inv = cur.fetchone()
    if not inv or inv[0] != 'pending':
        conn.rollback()
        cur.close()
        conn.close()
        return redirect(url_for('workspace', w_id=w_id))

    cur.execute(
        'UPDATE Channel_Invitation SET status = %s '
        'WHERE invitee_id = %s AND c_id = %s',
        ('accepted', invitee_id, c_id)
    )
    cur.execute(
        'INSERT INTO channel_member (c_id, a_id) VALUES (%s, %s)',
        (c_id, invitee_id)
    )

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('workspace', w_id=w_id))

@app.route('/reject_channel_invitation')
def reject_channel_invitation():
    inviter_id = request.args.get('inviter_id', -1)
    invitee_id = session.get('a_id', -1)
    w_id = request.args.get('w_id', -1)
    c_id = request.args.get('c_id', -1)

    conn = get_db()
    cur = conn.cursor()

    # Update the invitation status to accepted
    cur.execute('UPDATE Channel_Invitation '
                'SET status = %s '
                'WHERE invitee_id = %s AND c_id = %s AND inviter_id = %s', 
                ('declined', invitee_id, c_id, inviter_id))
    
    cur.close()
    conn.commit()
    conn.close()
    return redirect(url_for('workspace', w_id=w_id))

@app.route('/post_message', methods=['POST'])
def post_message():
    content = request.form['content']
    c_id = session.get('c_id')
    a_id = session.get('a_id')

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO Message (c_id, sender_id, content) VALUES (%s, %s, %s) RETURNING m_id, timestamp',
        (c_id, a_id, content)
    )
    row = cur.fetchone()
    cur.execute('SELECT username, nickname FROM Account WHERE a_id = %s', (a_id,))
    account = cur.fetchone()
    cur.close()
    conn.commit()
    conn.close()

    if request.headers.get('X-Requested-With') == 'fetch':
        display_name = account[1] if account[1] else account[0]
        return jsonify({
            'content': content,
            'timestamp': str(row[1]),
            'display_name': display_name
        })

    return redirect(url_for('channel', w_id=session.get('w_id'), c_id=c_id))

if __name__ == "__main__":
    import sys
    app.run(debug=True)