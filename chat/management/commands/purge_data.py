from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection

class Command(BaseCommand):
    help = 'Purge all user and post related data by directly truncating tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-superuser',
            action='store_true',
            help='Keep superusers in the database',
        )

    def handle(self, *args, **options):
        keep_superuser = options.get('keep_superuser', False)
        
        # Execute raw SQL for faster deletion
        with connection.cursor() as cursor:
            # Disable foreign key checks temporarily (this works for both SQLite and PostgreSQL)
            cursor.execute("PRAGMA foreign_keys = OFF;") if connection.vendor == 'sqlite' else cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
            
            # Delete all data from various tables
            self.stdout.write('Purging all data tables...')
            
            # Chat-related tables
            cursor.execute("DELETE FROM chat_message;")
            cursor.execute("DELETE FROM chat_chatroom_participants;")
            cursor.execute("DELETE FROM chat_chatroom;")
            
            # Post-related tables
            cursor.execute("DELETE FROM chat_postshare;")
            cursor.execute("DELETE FROM chat_repost;")
            cursor.execute("DELETE FROM chat_commentreaction;")
            cursor.execute("DELETE FROM chat_comment;")
            cursor.execute("DELETE FROM chat_postreaction;")
            cursor.execute("DELETE FROM chat_blockedpost;")
            cursor.execute("DELETE FROM chat_post;")
            
            # Friend-related tables
            cursor.execute("DELETE FROM chat_friendrequest;")
            cursor.execute("DELETE FROM chat_friendlist_friends;")
            cursor.execute("DELETE FROM chat_friendlist;")
            cursor.execute("DELETE FROM chat_profile_blocked_users;")
            cursor.execute("DELETE FROM chat_profile_friends;")
            
            # Handle user profiles and users
            if keep_superuser:
                # Get superuser IDs to preserve
                cursor.execute("SELECT id FROM auth_user WHERE is_superuser = 1;")
                superuser_ids = [row[0] for row in cursor.fetchall()]
                
                if superuser_ids:
                    placeholders = ','.join(['%s'] * len(superuser_ids))
                    cursor.execute(f"DELETE FROM chat_profile WHERE user_id NOT IN ({placeholders});", superuser_ids)
                    cursor.execute(f"DELETE FROM auth_user WHERE id NOT IN ({placeholders}) AND is_superuser = 0;", superuser_ids)
                    
                    self.stdout.write(f'Deleted all data except superusers (kept {len(superuser_ids)} superusers)')
                else:
                    self.stdout.write('No superusers found, deleting all users')
                    cursor.execute("DELETE FROM chat_profile;")
                    cursor.execute("DELETE FROM auth_user;")
            else:
                # Delete all users and profiles
                cursor.execute("DELETE FROM chat_profile;")
                cursor.execute("DELETE FROM auth_user;")
            
            # Re-enable foreign key checks
            cursor.execute("PRAGMA foreign_keys = ON;") if connection.vendor == 'sqlite' else cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")
            
            self.stdout.write(self.style.SUCCESS('Successfully purged all data from the database!'))
            
            # Optionally reset sequences for PostgreSQL
            if connection.vendor == 'postgresql':
                self.stdout.write('Resetting PostgreSQL sequences...')
                cursor.execute("""
                    DO $$
                    DECLARE
                        statements CURSOR FOR
                            SELECT 'SELECT SETVAL(' ||
                                   quote_literal(quote_ident(PGT.schemaname) || '.' || quote_ident(S.relname)) ||
                                   ', COALESCE(MAX(' ||quote_ident(C.attname)|| '), 1) ) FROM ' ||
                                   quote_ident(PGT.schemaname)|| '.'||quote_ident(T.relname)|| ';'
                            FROM pg_class AS S,
                                 pg_depend AS D,
                                 pg_class AS T,
                                 pg_attribute AS C,
                                 pg_tables AS PGT
                            WHERE S.relkind = 'S'
                                AND S.oid = D.objid
                                AND D.refobjid = T.oid
                                AND D.refobjid = C.attrelid
                                AND D.refobjsubid = C.attnum
                                AND T.relname = PGT.tablename
                            ORDER BY S.relname;
                    BEGIN
                        FOR stmt IN statements LOOP
                            EXECUTE stmt.column_1;
                        END LOOP;
                    END $$;
                """)
                self.stdout.write('PostgreSQL sequences reset.')
                
        self.stdout.write(self.style.SUCCESS('Database cleaned successfully!')) 