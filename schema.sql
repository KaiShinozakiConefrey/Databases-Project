DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

CREATE TABLE Account (
    a_id SERIAL NOT NULL PRIMARY KEY,
    email_address VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    nickname VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE Workspace (
    w_id SERIAL NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255)
);

CREATE TABLE workspace_member(
    w_id INT NOT NULL,
    a_id INT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'co_admin', 'member')),
    PRIMARY KEY (w_id, a_id),
    FOREIGN KEY (w_id) REFERENCES Workspace(w_id) ON DELETE CASCADE,
    FOREIGN KEY (a_id) REFERENCES Account(a_id) ON DELETE CASCADE
);

CREATE TABLE workspace_invitation(
    inviter_id INT NOT NULL,
    invitee_id INT NOT NULL,
    w_id INT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'accepted', 'declined')),
    PRIMARY KEY (inviter_id, invitee_id, w_id),
    FOREIGN KEY (inviter_id) REFERENCES Account(a_id) ON DELETE CASCADE,
    FOREIGN KEY (invitee_id) REFERENCES Account(a_id) ON DELETE CASCADE,
    FOREIGN KEY (w_id) REFERENCES Workspace(w_id) ON DELETE CASCADE
);

CREATE TABLE channel (
    c_id SERIAL NOT NULL PRIMARY KEY,
    w_id INT NOT NULL,
    creator_id INT NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    channel_description VARCHAR(255),
    type VARCHAR(20) NOT NULL CHECK (type IN ('public', 'private', 'direct')),
    FOREIGN KEY (w_id) REFERENCES Workspace(w_id) ON DELETE CASCADE,
    FOREIGN KEY (creator_id) REFERENCES Account(a_id) ON DELETE CASCADE
);

CREATE TABLE channel_member (
    c_id INT NOT NULL,
    a_id INT NOT NULL,
    PRIMARY KEY (c_id, a_id),
    FOREIGN KEY (c_id) REFERENCES channel(c_id) ON DELETE CASCADE,
    FOREIGN KEY (a_id) REFERENCES Account(a_id) ON DELETE CASCADE
);

CREATE TABLE channel_invitation (
    inviter_id INT NOT NULL,
    invitee_id INT NOT NULL,
    c_id INT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'accepted', 'declined')),
    PRIMARY KEY (inviter_id, invitee_id, c_id),
    FOREIGN KEY (inviter_id) REFERENCES Account(a_id) ON DELETE CASCADE,
    FOREIGN KEY (invitee_id) REFERENCES Account(a_id) ON DELETE CASCADE,
    FOREIGN KEY (c_id) REFERENCES channel(c_id) ON DELETE CASCADE
);
CREATE TABLE message (
    m_id SERIAL NOT NULL PRIMARY KEY,
    c_id INT NOT NULL,
    sender_id INT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (c_id) REFERENCES channel(c_id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES Account(a_id) ON DELETE CASCADE
);