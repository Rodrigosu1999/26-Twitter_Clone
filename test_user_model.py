"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py

from app import app
import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows, Likes

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        u1 = User.signup(
            "test_user1", "test_email1@email.com", "test_password", None)
        u2 = User.signup(
            "test_user2", "test_email2@email.com", "test_password", None)

        db.session.commit()

        self.u1 = u1
        self.u2 = u2

        self.client = app.test_client()

    def tearDown(self):
        """Clean up any fouled transaction."""

        db.session.rollback()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    def test_follow(self):
        """Testing if the user's following works"""
        # We are making use1 follow user 2
        self.u1.following.append(self.u2)
        db.session.commit()
        # User 1's following list should have user 2
        self.assertEqual(self.u1.following[0].id, self.u2.id)
        # User's 2 follower list should have user 1
        self.assertEqual(self.u2.followers[0].id, self.u1.id)

    def test_is_following(self):
        """Testing if the 'is_following' method works"""
        # We are making use1 follow user 2
        self.u1.following.append(self.u2)
        db.session.commit()
        # User 1 shold be following user 2
        self.assertTrue(self.u1.is_following(self.u2))
        # User 2 shouldn't be following user 1
        self.assertFalse(self.u2.is_following(self.u1))

    def test_is_followed_by(self):
        """Testing if the 'is_followed_by' method works"""
        # We are making use1 follow user 2
        self.u1.following.append(self.u2)
        db.session.commit()
        #
        self.assertTrue(self.u2.is_followed_by(self.u1))
        self.assertFalse(self.u1.is_followed_by(self.u2))

    def test_signup(self):
        """Test if the signup method creates a new user"""
        # We create a new user
        user = User.signup(
            "test_user3", "test_email3@email.com", "test_password", None)

        db.session.commit()
        # We chec if the information we gave is correct
        self.assertEqual(user.username, "test_user3")
        self.assertEqual(user.email, "test_email3@email.com")
        self.assertNotEqual(user.password, "test_password")
        # We got a default image url when a image is not given
        self.assertIsNotNone(user.image_url)
        # The new user shouldn't have any users or followers
        self.assertEqual(len(user.followers), 0)
        self.assertEqual(len(user.following), 0)

    def test_invalid_username_signup(self):
        """Test if the signup method doesn't create a new user when a username value is invalid"""
        # We create a new user with an invalid username
        user = User.signup(
            None, "test_email3@email.com", "test_password", None)
        # We should get an exception
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_invalid_email_signup(self):
        """Test if the signup method doesn't create a new user when a email value is invalid"""
        # We create a new user with an invalid email
        user = User.signup(
            "test_user3", None, "test_password", None)
        # We should get an exception
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_invalid_passwordl_signup(self):
        """Test if the signup method doesn't create a new user when a password value is invalid"""
        # We should get an exception when we give an empty password as we have it "Nullable=False"
        with self.assertRaises(ValueError) as context:
            user = User.signup(
                "test_user3", "test_email3@email.com", None, None)

    def test_authentication(self):
        """We are testing the authenticate method for Loging In"""
        user = User.authenticate(self.u1.username, "test_password")
        # With a valid authentication we should get our user back
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "test_user1")

    def test_invalid_authentication(self):
        bad_user = User.authenticate("wrong", "test_password")
        # With an invalid authentication False should be returned
        self.assertFalse(bad_user)
        bad_password = User.authenticate(self.u1.username, "wrong")
        self.assertFalse(bad_password)
