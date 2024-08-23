CREATE DATABASE IF NOT EXISTS benfordapp;

USE benfordapp;

DROP TABLE IF EXISTS tokens;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS users;

CREATE TABLE users
(
    userid       int not null AUTO_INCREMENT,
    username     varchar(64) not null,
    pwdhash      varchar(256) not null,
    PRIMARY KEY  (userid),
    UNIQUE       (username)
);

ALTER TABLE users AUTO_INCREMENT = 80001;  -- starting value

CREATE TABLE jobs
(
    jobid             int not null AUTO_INCREMENT,
    userid            int not null,
    status            varchar(256) not null,  -- uploaded, completed, error, processing...
    jobtype           varchar(256) not null,  -- sentiment, summary, benford, entity
    originaldatafile  varchar(256) not null,  -- original PDF filename from user
    datafilekey       varchar(256) not null,  -- PDF filename in S3 (bucketkey)
    resultsfilekey    varchar(256) not null,  -- results filename in S3 bucket
    PRIMARY KEY (jobid),
    FOREIGN KEY (userid) REFERENCES users(userid),
    UNIQUE      (datafilekey)
);

ALTER TABLE jobs AUTO_INCREMENT = 1001;  -- starting value

CREATE TABLE tokens
(
    token             varchar(128) not null,  -- authentication token
    userid            int not null,           -- user that token identifies
    expiration_utc    datetime not null,      -- token's expiration date/time UTC
    PRIMARY KEY (token),
    FOREIGN KEY (userid) REFERENCES users(userid)
);

--
-- Insert some users to start with:
-- 
-- PWD hashing: https://phppasswordhash.com/
--
INSERT INTO users(username, pwdhash)  -- pwd = abc123!!
            values('p_sarkar', '$2y$10$/8B5evVyaHF.hxVx0i6dUe2JpW89EZno/VISnsiD1xSh6ZQsNMtXK');

INSERT INTO users(username, pwdhash)  -- pwd = abc456!!
            values('e_ricci', '$2y$10$F.FBSF4zlas/RpHAxqsuF.YbryKNr53AcKBR3CbP2KsgZyMxOI2z2');

INSERT INTO users(username, pwdhash)  -- pwd = abc789!!
            values('l_chen', '$2y$10$GmIzRsGKP7bd9MqH.mErmuKvZQ013kPfkKbeUAHxar5bn1vu9.sdK');

--
-- creating user accounts for database access:
--
-- ref: https://dev.mysql.com/doc/refman/8.0/en/create-user.html
--

DROP USER IF EXISTS 'benfordapp-read-only';
DROP USER IF EXISTS 'benfordapp-read-write';

CREATE USER 'benfordapp-read-only' IDENTIFIED BY 'abc123!!';
CREATE USER 'benfordapp-read-write' IDENTIFIED BY 'def456!!';

GRANT SELECT, SHOW VIEW ON benfordapp.* 
      TO 'benfordapp-read-only';
GRANT SELECT, SHOW VIEW, INSERT, UPDATE, DELETE, DROP, CREATE, ALTER ON benfordapp.* 
      TO 'benfordapp-read-write';
      
FLUSH PRIVILEGES;

--
-- done
--
