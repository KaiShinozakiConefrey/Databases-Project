--- Create a new user account with email, name, nickname and password
INSERT INTO Account(email_address, username, nickname, password)
VALUES ('tess@gmail.com', 'Tesspasser', 'Tess', '12345678');

--- Create a new public channel inside a workspace by a particular user, making sure they are authorized.
INSERT INTO channel(w_id, creator_id, channel_name, channel_description, type)
SELECT 1, 6, 'Art', 'Art discussion channel', 'public'
WHERE EXISTS
( SELECT 1 FROM workspace_member WHERE w_id = 1 AND a_id = 6 AND role IN ('admin', 'co_admin'));

--- List all administrators for each workspace
SELECT w.name as workspace, a.username as administrator, wm.role
FROM workspace_member wm 
    JOIN workspace w ON wm.w_id = w.w_id
JOIN Account a on wm.a_id = a.a_id
WHERE wm.role = 'admin' OR wm.role = 'co_admin'
ORDER BY workspace;

--- For each public channel in a workspace, list number of users
--- that were invited to join more than 5 days ago but have not yet joined
SELECT w.name AS workspace, c.channel_name as channel, COUNT(*) AS pending_invitations
FROM workspace w JOIN channel c ON w.w_id = c.c_id
    JOIN channel_invitation ci ON ci.c_id = c.c_id
WHERE ci.timestamp < NOW() - INTERVAL '5 days'
    AND c.type = 'public'
GROUP BY workspace, channel;

--- For a particular channel, list all messages in chronological order
SELECT a.username, m.content, timestamp
FROM message m 
    JOIN channel c ON m.c_id = c.c_id 
    JOIN Account a ON a.a_id = m.sender_id
WHERE c.c_id = 2
ORDER BY timestamp;

--- For a particular user, list all messages they have posted in any chanel
SELECT w.name as workspace, c.channel_name as channel, a.username, m.content, timestamp
FROM message m 
    JOIN channel c ON m.c_id = c.c_id 
    JOIN Account a ON a.a_id = m.sender_id
    JOIN Workspace w ON w.w_id = c.w_id
WHERE a.a_id = 3
ORDER BY workspace, channel, timestamp;

--- For a particular user, list all messages that are accessible to this user and that contain the keyword “perpendicular”
SELECT a.username AS user, w.name as workspace, c.channel_name as channel, b.username AS sender, m.content, timestamp
FROM Account a
    JOIN channel_member cm ON a.a_id = cm.a_id
    JOIN channel c ON c.c_id = cm.c_id
    JOIN message m ON m.c_id = c.c_id
    JOIN Account b on m.sender_id = b.a_id
    JOIN Workspace w ON w.w_id = c.w_id
WHERE a.a_id = 7 AND content ILIKE '%perpendicular%'
ORDER BY workspace, channel, timestamp;