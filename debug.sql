SELECT * FROM Account;

-- Get workspace invitations
SELECT a.username as invitee, 
    b.username as inviter, 
    w.name as workspace,
    wi.status,
    wi.timestamp
FROM Workspace_Invitation wi 
JOIN Account a ON wi.invitee_id = a.a_id
JOIN Account b ON wi.inviter_id = b.a_id
JOIN Workspace w on wi.w_id = w.w_id;

-- Get channel invitations
SELECT a.username as invitee, 
    b.username as inviter, 
    c.channel_name as channel,
    w.name as workspace,
    ci.status,
    ci.timestamp
FROM Channel_Invitation ci 
JOIN Account a ON ci.invitee_id = a.a_id
JOIN Account b ON ci.inviter_id = b.a_id
JOIN Channel c on ci.c_id = c.c_id
JOIN Workspace w on w.w_id = c.w_id;

-- Get all channels on workspaces
SELECT c.channel_name as channel, w.name as workspace
FROM channel c JOIN workspace w on c.w_id = w.w_id
ORDER BY workspace;

SELECT * FROM message;

DELETE FROM message WHERE content = ''

SELECT * FROM Channel_Member;

SELECT DISTINCT c.channel_name, w.name
FROM Channel_Member cm JOIN Account a ON a.a_id = cm.a_id
    JOIN Channel c on cm.c_id = cm.c_id 
    JOIN Workspace w ON c.w_id = w.w_id
WHERE a.username != 'Auta';

SELECT * FROM message
ORDER BY timestamp;

INSERT INTO message(c_id, sender_id, content, timestamp)
VALUES(2, 3, 'Anyone else feeling rather perpendicular', '2026-04-23 23:45:32')

SELECT * FROM workspace_member;

UPDATE Account
SET password = (SELECT password FROM Account WHERE username = 'Ririkats');


SELECT * FROM channel_invitation

DELETE FROM Channel_Invitation
WHERE inviter_id = (SELECT a_id FROM Account WHERE username = 'Ririkats')
  AND invitee_id = (SELECT a_id FROM Account WHERE username = 'kaishuusc');

SELECT * FROM channel

UPDATE channel_invitation
SET status = 'accepted'
WHERE c_id = 9;

UPDATE channel
SET type = 'direct'
WHERE c_id = 11;