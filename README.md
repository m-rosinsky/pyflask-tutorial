# Pyflask-tutorial

## Goal

My goal with this project is to learn more about backend system design by starting with the base project provided by the Python flask docs (https://flask.palletsprojects.com/en/3.0.x/tutorial/) and expanding it.

## Navigation

Each progression of the project is snapshotted into its own branch.

The branch name is in parentheses after the section name, so the state of the application that corresponds to the specific section of the README can be found.

## Base Project (branch: 0-base-app)

The base project is a simple forum-style application that allows users to make posts. The current features are:

- Login/Register users
- Create posts
- Edit posts
- Delete posts
- View all posts

Here are a few screenshots (This is definitely not a frontend project):

| ![Registration Page](./imgs/register.png) |
| :--: |
| _A basic registration page_ |

| ![Main page](./imgs/posts.png) |
| :--: |
| _The main page showcasing the feed of posts_ |

Currently, this is a monolithic architecture, since it uses a local sqlite instance running on the same server as the web application.

Here is a current snapshot of the application, which I will continue to update as more components are added:

![Diagram 0](./imgs/diag_0.png)

## 