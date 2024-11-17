from flask import Flask, redirect, render_template, request, url_for, session, flash, jsonify
from sqlalchemy import create_engine, text
import os
from functools import wraps

app = Flask(__name__)

# Configure the database connection
DATABASE_URL = "postgresql://cv2599:cv2599@w4111.cisxo09blonu.us-east-1.rds.amazonaws.com/w4111"
engine = create_engine(DATABASE_URL)

app.secret_key = os.urandom(12)

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("index.html")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    # Check if user is already logged in, log them out if they access login page again
    if 'user_id' in session:
        session.clear()  # Clear session if accessing login page while logged in
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check in the database for user credentials using a parameterized query
        with engine.connect() as connection:
            query = text("SELECT user_id, spec_user FROM Users WHERE email = :email AND password = :password")
            result = connection.execute(query, {"email": email, "password": password}).fetchone()

            if result:
                user_id, spec_user = result
                session['user_id'] = user_id
                session['spec_user'] = spec_user

                if spec_user == "Guest":
                    guest_query = text("SELECT guest_id FROM Guest WHERE user_id = :user_id")
                    guest_result = connection.execute(guest_query, {"user_id": user_id}).fetchone()
                    if guest_result:
                        session['guest_id'] = guest_result[0]
                    else:
                        flash("Guest not found.", "danger")
                        return redirect(url_for("login"))

                    return redirect(url_for("guest_home"))
                elif spec_user == 'Staff':
                    staff_result = connection.execute(text("SELECT spec_staff, staff_id FROM Staff_workat WHERE user_id = :user_id"), {"user_id": user_id})
                    staff_info = staff_result.fetchone()
                    spec_staff = staff_info[0].strip() if staff_info else None

                    if spec_staff == 'Liaison':
                        return redirect(url_for('liaison_dashboard'))

                    if spec_staff == 'Marketing':
                        marketing_result = connection.execute(text("SELECT marketing_id, level FROM marketing WHERE staff_id = :staff_id"), {"staff_id": staff_info[1]}).fetchone()
                        level = marketing_result[1]

                        if level < 7:
                            return redirect(url_for('marketing_below'))
                        else:
                            return redirect(url_for('marketing_above'))
            else:
                flash("Invalid email or password, please try again.", "danger")
                return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/guestregister", methods=["GET", "POST"])
def guest_register():
    if request.method == 'POST':
        # Retrieve form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        phonenumber = request.form.get('phonenumber')
        spec_user = "Guest"  # Default value for all entries

        # Insert the new user into the Users table using parameterized queries
        with engine.connect() as connection:
            insert_user_query = text("""
                INSERT INTO Users (first_name, last_name, spec_user, password, phonenumber, email) 
                VALUES (:first_name, :last_name, :spec_user, :password, :phonenumber, :email) 
                RETURNING user_id
            """)
            result = connection.execute(insert_user_query, {
                "first_name": first_name,
                "last_name": last_name,
                "spec_user": spec_user,
                "password": password,
                "phonenumber": phonenumber,
                "email": email
            })
            user_id = result.fetchone()[0]  # Get the generated user_id

            # Insert guest record using the user_id generated above
            update_guest_query = text("""
                INSERT INTO Guest (user_id) 
                VALUES (:user_id)
                RETURNING guest_id
            """)
            result = connection.execute(update_guest_query, {"user_id": user_id})
            guest_id = result.fetchone()[0]  # Get the generated guest_id

        # Redirect to home page after successful registration
        return redirect(url_for('home'))

    return render_template("guestregister.html")

@app.route("/guesthome")
@login_required
def guest_home():
    # Check if user is logged in and is a guest
    if 'user_id' in session and session.get('spec_user') == 'Guest':
        user_id = session['user_id']
        with engine.connect() as connection:
            welcome_query = text("""
                SELECT first_name FROM Users WHERE user_id = :user_id
            """)
            result = connection.execute(welcome_query, {"user_id": user_id})
            guestname = result.fetchone()
        return render_template("guesthome.html", gname=guestname[0])
    else:
        return redirect(url_for('login'))

@app.route("/client_page", methods=["GET", "POST"])
def client_page():
    if 'guest_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    guest_id = session['guest_id']

    with engine.connect() as connection:
        # Check if guest_id is in the Client table using a parameterized query
        client_query = text("""
            SELECT client_id FROM Client WHERE guest_id = :guest_id
        """)
        result = connection.execute(client_query, {"guest_id": guest_id})
        client_row = result.fetchone()
        

        if client_row:
            # Get client_id
            client_id = client_row[0]

            print("client_id", client_id)

            # Query for Personal Inventory using a parameterized query
            personal_inventory_query = text("""
                SELECT i.name, i.artist, i.photo_url, i.location, i.volume, 
                       i.comment, i.net_worth, io.status
                FROM Item_in i
                JOIN Inventory_owned io ON i.inventory_id = io.inventory_id
                JOIN Client c ON io.client_id = c.client_id
                WHERE c.client_id = :client_id
            """)
            personal_inventory = connection.execute(personal_inventory_query, {"client_id": client_id}).fetchall()

            # Query for Browse Art Pieces using a parameterized query
            browse_art_pieces_query = text("""
                SELECT a.name AS art_piece_name, ar.name AS artist_name, a.type, 
                       a.genre, a.price, a.photo_url, a.art_id
                FROM ArtPieces_Produce a
                JOIN Artists_Collaborates ar ON a.artist_id = ar.artist_id
                WHERE ar.liason_id is NOT NULL
            """)
            browse_art_pieces = connection.execute(browse_art_pieces_query).fetchall()

            return render_template("client.html", client_id=client_id, 
                                   personal_inventory=personal_inventory, 
                                   browse_art_pieces=browse_art_pieces)
        else:
            # If guest_id is not in Client, prompt for bank account number
            if request.method == "POST":
                bank_account = request.form.get("bank_account")
                if bank_account:
                    # Insert new entry into Client table using parameterized query
                    insert_client_query = text("""
                        INSERT INTO Client (guest_id, bank_account) VALUES (:guest_id, :bank_account)
                        RETURNING client_id
                    """)
                    result = connection.execute(insert_client_query, {
                        "guest_id": guest_id,
                        "bank_account": bank_account
                    })
                    client_id = result.fetchone()[0]  # Get the generated client_id
                    return render_template("client.html", client_id=client_id)

            # If not a POST request, render the modal to collect bank account
            return render_template("client_modal.html")

@app.route("/visitor", methods=["GET"])
def visitor():
    if 'guest_id' not in session:
        return redirect(url_for("login"))

    # Retrieve exhibitions and tickets for the user
    with engine.connect() as connection:
        # Get the visitor_id from the Visitor table based on the guest_id in the session
        visitor_query = text("""
            SELECT visitor_id FROM Visitor WHERE guest_id = :guest_id
        """)
        visitor_result = connection.execute(visitor_query, {"guest_id": session['guest_id']})
        visitor_row = visitor_result.fetchone()

        if visitor_row:
            visitor_id = visitor_row[0]

            # Get tickets for the user
            my_tickets_query = text("""
                SELECT A.exhibition_id, E.name, E.exhib_date, E.start_time, E.end_time, E.description, 
                       G.name AS gallery_name, D.city
                FROM Attend A
                JOIN Exhibitions_Host E ON A.exhibition_id = E.exhibition_id
                JOIN ArtGallery G ON E.gallery_id = G.gallery_id
                JOIN Address D ON G.location = D.address_id
                WHERE A.visitor_id = :visitor_id
            """)
            my_tickets = connection.execute(my_tickets_query, {"visitor_id": visitor_id}).fetchall()

            # Get available exhibitions
            exhibitions_query = text("""
                SELECT E.exhibition_id, E.name, E.exhib_date, E.start_time, E.end_time, E.description, E.gallery_id,
                       G.name AS gallery_name, D.city
                FROM Exhibitions_Host E
                JOIN ArtGallery G ON E.gallery_id = G.gallery_id
                JOIN Address D ON G.location = D.address_id
                WHERE E.exhibition_id NOT IN (SELECT exhibition_id FROM Attend WHERE visitor_id = :visitor_id)
            """)
            exhibitions = connection.execute(exhibitions_query, {"visitor_id": visitor_id}).fetchall()

            return render_template("visitor.html", my_tickets=my_tickets, exhibitions=exhibitions)

    return render_template("visitor.html", my_tickets=[], exhibitions=[])


@app.route("/delete_ticket", methods=["POST"])
def delete_ticket():
    if 'guest_id' not in session:
        return redirect(url_for("login"))

    exhibition_id = request.form.get("exhibition_id")

    with engine.connect() as connection:
        # Get visitor_id from Visitor table
        visitor_query = text("""
            SELECT visitor_id FROM Visitor WHERE guest_id = :guest_id
        """)
        visitor_result = connection.execute(visitor_query, {"guest_id": session['guest_id']})
        visitor_row = visitor_result.fetchone()

        if visitor_row:
            visitor_id = visitor_row[0]

            # Delete the ticket from the Attend table
            delete_query = text("""
                DELETE FROM Attend WHERE exhibition_id = :exhibition_id AND visitor_id = :visitor_id
            """)
            connection.execute(delete_query, {"exhibition_id": exhibition_id, "visitor_id": visitor_id})
            connection.commit()

    return redirect(url_for("visitor"))


@app.route("/visitor", methods=["GET"])
def visitor_page():
    # Get search parameters from the form
    name = request.args.get('name')
    exhib_date = request.args.get('exhib_date')
    start_time = request.args.get('start_time')
    city = request.args.get('city')

    # Construct the base query with JOIN
    query = """
        SELECT e.exhibition_id, e.name, e.exhib_date, e.start_time, e.end_time, e.description, e.gallery_id, g.name AS gallery_name, a.city
        FROM Exhibitions_Host e
        JOIN ArtGallery g ON e.gallery_id = g.gallery_id
        JOIN Address a ON g.location = a.address_id
        WHERE (e.name ILIKE :name OR :name IS NULL)
          AND (e.exhib_date = :exhib_date OR :exhib_date IS NULL)
          AND (e.start_time = :start_time OR :start_time IS NULL)
          AND (a.city ILIKE :city OR :city IS NULL)
    """

    # Execute the query and fetch results
    with engine.connect() as connection:
        result = connection.execute(text(query), {
            "name": f"%{name}%" if name else None,
            "exhib_date": exhib_date if exhib_date else None,
            "start_time": start_time if start_time else None,
            "city": f"%{city}%" if city else None
        })
        exhibitions = result.fetchall()

    # Pass the results to the template
    return render_template("visitor.html", exhibitions=exhibitions)

@app.route("/get_ticket", methods=["POST"])
def get_ticket():
    if 'guest_id' not in session:
        return jsonify({"message": "User not logged in."}), 401

    guest_id = session['guest_id']
    data = request.get_json()
    exhibition_id = data.get('exhibition_id')
    gallery_id = data.get('gallery_id')

    try:
        with engine.connect() as connection:
            # Check if guest_id is already in Visitor table
            check_visitor_query = text("SELECT visitor_id FROM Visitor WHERE guest_id = :guest_id")
            result = connection.execute(check_visitor_query, {"guest_id": guest_id})
            visitor_row = result.fetchone()

            # If guest_id is not in Visitor table, insert it
            if visitor_row is None:
                insert_visitor_query = text("INSERT INTO Visitor (guest_id) VALUES (:guest_id) RETURNING visitor_id")
                result = connection.execute(insert_visitor_query, {"guest_id": guest_id})
                visitor_id = result.fetchone()[0]
            else:
                visitor_id = visitor_row[0]

            # Insert into Attend table
            insert_attend_query = text("""
                INSERT INTO Attend (exhibition_id, gallery_id, visitor_id)
                VALUES (:exhibition_id, :gallery_id, :visitor_id)
            """)
            connection.execute(insert_attend_query, {
                "exhibition_id": exhibition_id,
                "gallery_id": gallery_id,
                "visitor_id": visitor_id
            })
            connection.commit()

            # Fetch the details of the booked exhibition to send back to the client
            exhibition_query = text("""
                SELECT E.name, E.exhib_date, E.start_time, E.end_time, E.description, 
                       G.name AS gallery_name, D.city
                FROM Exhibitions_Host E
                JOIN ArtGallery G ON E.gallery_id = G.gallery_id
                JOIN Address D ON G.location = D.address_id
                WHERE E.exhibition_id = :exhibition_id
            """)
            exhibition = connection.execute(exhibition_query, {"exhibition_id": exhibition_id}).fetchone()

            if exhibition:
                return jsonify({
                    "message": "Ticket successfully booked!",
                    "exhibition": {
                        "name": exhibition.name,
                        "exhib_date": exhibition.exhib_date.strftime("%Y-%m-%d"),
                        "start_time": exhibition.start_time.strftime("%H:%M:%S"),
                        "end_time": exhibition.end_time.strftime("%H:%M:%S"),
                        "description": exhibition.description,
                        "gallery_name": exhibition.gallery_name,
                        "city": exhibition.city
                    }
                })
            else:
                return jsonify({"message": "Exhibition not found."}), 404

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/liaison_dashboard', methods=["GET", "POST"])
def liaison_dashboard():
    user_id = session['user_id']
    with engine.connect() as connection:
        staff_result = connection.execute(text("""
        SELECT spec_staff, staff_id 
        FROM Staff_workat 
        WHERE user_id = :user_id
        """), {"user_id": user_id})
                        
        staff_info = staff_result.fetchone()
        if not staff_info:
            return jsonify({"message": "Staff not found."}), 404

        liaison_result = connection.execute(text("""
            SELECT liaison_id, speciality 
            FROM liaison 
            WHERE staff_id = :staff_id
        """), {"staff_id": staff_info.staff_id})
        
        liaison_info = liaison_result.fetchone()
        if not liaison_info:
            return jsonify({"message": "Liaison not found."}), 404

        result = connection.execute(text("""
            SELECT 
                ac.artist_id, ac.liason_id, ac.name, ac.email, ac.nationality, ac.salary, ac.studio_loc, ac.priority_level, 
                ap.art_id, ap.name as art_name, ap.date, ap.type, ap.genre, ap.price, ap.photo_url
            FROM artists_collaborates ac
            JOIN artpieces_produce ap ON ac.artist_id = ap.artist_id
            WHERE liason_id = :liaison_id
        """), {"liaison_id": liaison_info.liaison_id})
                                
        artists = result.fetchall()

        candidates_result = connection.execute(text("""
            WITH artist_genres AS (
                SELECT ac.artist_id, ac.name, COUNT(*) AS total_artworks, 
                       COUNT(CASE WHEN ap.genre = :speciality THEN 1 END) AS matching_artworks
                FROM artists_collaborates ac
                JOIN artpieces_produce ap ON ac.artist_id = ap.artist_id
                WHERE ac.liason_id IS NULL
                GROUP BY ac.artist_id, ac.name
            )
            SELECT artist_id, name
            FROM artist_genres
            WHERE matching_artworks > 0
        """), {"speciality": liaison_info.speciality.strip()})

        candidates = candidates_result.fetchall()

    return render_template(
        'liaison_dashboard.html',
        liaison_id=liaison_info.liaison_id,
        speciality=liaison_info.speciality,
        artists=artists,
        candidates=candidates
    )

@app.route('/remove_collaboration/<int:artist_id>', methods=["POST"])
def remove_collaboration(artist_id):
    with engine.connect() as connection:
        connection.execute(text("""
            UPDATE artists_collaborates
            SET liason_id = NULL
            WHERE artist_id = :artist_id
        """), {"artist_id": artist_id})
        connection.commit()
    return jsonify({"success": True})

@app.route('/add_collaboration', methods=["POST"])
def add_collaboration():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Unauthorized"})

    user_id = session['user_id']
    data = request.get_json()
    artist_id = data.get('artist_id')

    if not artist_id:
        return jsonify({"success": False, "error": "No artist ID provided"})

    with engine.connect() as connection:
        # Safely fetch liaison information
        liaison_result = connection.execute(text("""
            SELECT liaison_id 
            FROM liaison 
            WHERE staff_id = (SELECT staff_id FROM Staff_workat WHERE user_id = :user_id)
        """), {"user_id": user_id})
        
        liaison_info = liaison_result.fetchone()
        if not liaison_info:
            return jsonify({"success": False, "error": "Liaison not found"})

        liaison_id = liaison_info[0]

        # Safely update the artist's liaison association
        update_query = text("""
            UPDATE artists_collaborates 
            SET liason_id = :liaison_id 
            WHERE artist_id = :artist_id
        """)
        connection.execute(update_query, {"liaison_id": liaison_id, "artist_id": artist_id})
        connection.commit()

    return jsonify({"success": True})

@app.route('/marketing_below', methods=["GET", "POST"])
def marketing_below():
    if 'user_id' not in session:
        return "User not logged in.", 401

    user_id = session['user_id']
    with engine.connect() as connection:
        # Safely retrieve staff information
        staff_result = connection.execute(text("""
            SELECT spec_staff, staff_id 
            FROM Staff_workat 
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        
        staff_info = staff_result.fetchone()
        if not staff_info:
            return "Staff information not found for the current user.", 404
        
        spec_staff = staff_info[0].strip()

        # Safely retrieve marketing information
        marketing_result = connection.execute(text("""
            SELECT marketing_id, level 
            FROM marketing 
            WHERE staff_id = :staff_id
        """), {"staff_id": staff_info[1]})
        
        marketing_info = marketing_result.fetchone()
        if not marketing_info:
            return "Marketing information not found for the staff member.", 404

        # Safely retrieve managed exhibitions
        managed_result = connection.execute(text("""
            SELECT eh.name AS exhibition_name, ag.name AS gallery_name, eh.exhib_date AS exhibition_date, 
                   eh.start_time, eh.end_time, m.marketing_id, eh.exhibition_id
            FROM Exhibitions_Host eh
            JOIN ArtGallery ag ON eh.gallery_id = ag.gallery_id
            JOIN Manage m ON eh.exhibition_id = m.exhibition_id AND eh.gallery_id = m.gallery_id
            WHERE m.marketing_id = :marketing_id
        """), {"marketing_id": marketing_info[0]})
        
        managed_below_exhib = managed_result.fetchall()

        # Safely retrieve candidate exhibitions available to manage
        candidate_below_result = connection.execute(text("""
            WITH managed_exhib AS (
                SELECT m.exhibition_id, m.gallery_id, eh.name AS exhibition_name, 
                       eh.exhib_date, eh.start_time AS exhibition_start, 
                       eh.end_time AS exhibition_end, eh.description, m.marketing_id AS existing_marketing_id
                FROM Manage m 
                JOIN Marketing m2 ON m.marketing_id = m2.marketing_id
                JOIN Exhibitions_Host eh ON m.exhibition_id = eh.exhibition_id 
                                          AND m.gallery_id = eh.gallery_id
                WHERE m.marketing_id != :marketing_id 
                  AND m2.level >= 7
                  AND m.exhibition_id NOT IN (
                      SELECT exhibition_id
                      FROM Manage
                      WHERE marketing_id = :marketing_id
                  )
            ),
            my_shifts AS (
                SELECT s.shift_date, s.start_time, s.end_time, sw.staff_id
                FROM Shifts s
                JOIN When_work w ON s.shift_id = w.shift_id
                JOIN Staff_workat sw ON w.staff_id = sw.staff_id
                JOIN Marketing m ON sw.staff_id = m.staff_id
                WHERE m.marketing_id = :marketing_id
            )
            SELECT me.exhibition_id, me.exhib_date, me.exhibition_start, me.exhibition_end,
                   ag.name AS gallery_name, ms.staff_id, me.exhibition_name, 
                   me.existing_marketing_id, ms.start_time, ms.end_time
            FROM managed_exhib me
            JOIN my_shifts ms ON me.exhib_date = ms.shift_date
            JOIN ArtGallery ag ON me.gallery_id = ag.gallery_id
            WHERE me.exhibition_start >= ms.start_time 
              AND me.exhibition_end <= ms.end_time
        """), {"marketing_id": marketing_info[0]})
        
        candidate_below_info = candidate_below_result.fetchall()

        return render_template(
            'marketing_below.html', 
            managed_below_exhib=managed_below_exhib, 
            candidate_below_info=candidate_below_info
        )


@app.route('/marketing_above', methods=["GET", "POST"])
def marketing_above():
    user_id = session['user_id']
    with engine.connect() as connection:
        # Fetch staff information securely
        staff_result = connection.execute(text("""
            SELECT spec_staff, staff_id 
            FROM Staff_workat 
            WHERE user_id = :user_id
        """), {"user_id": user_id})
                        
    staff_info = staff_result.fetchone()
    spec_staff = staff_info[0].strip() if staff_info else None

    with engine.connect() as connection:
        # Fetch marketing level securely
        marketing_result = connection.execute(text("""
            SELECT marketing_id, level 
            FROM marketing 
            WHERE staff_id = :staff_id
        """), {"staff_id": staff_info[1]})
        
        marketing_info = marketing_result.fetchone()
        marketing_id = marketing_info[0]

        # Retrieve exhibitions managed by the marketing member
        managed_result = connection.execute(text("""
            SELECT eh.name AS exhibition_name, ag.name AS gallery_name, eh.exhib_date AS exhibition_date, 
                   eh.start_time, eh.end_time, m.marketing_id, eh.exhibition_id
            FROM Exhibitions_Host eh
            JOIN ArtGallery ag ON eh.gallery_id = ag.gallery_id
            JOIN Manage m ON eh.exhibition_id = m.exhibition_id AND eh.gallery_id = m.gallery_id
            WHERE m.marketing_id = :marketing_id
        """), {"marketing_id": marketing_id})

        managed_exhib = managed_result.fetchall() 

        exhibitions_info = {}
        for exhibition in managed_exhib:
            exhibition_id = exhibition.exhibition_id  

            # Retrieve staff with a marketing level below 7 who are not managing this exhibition
            below7_staff_query = text("""
                SELECT m.marketing_id, sw.staff_id, s.first_name, s.last_name
                FROM Manage m
                JOIN Marketing mk ON m.marketing_id = mk.marketing_id
                JOIN Staff_workat sw ON mk.staff_id = sw.staff_id
                JOIN Users s ON sw.user_id = s.user_id
                WHERE m.exhibition_id = :exhibition_id
                  AND mk.level < 7
            """)
            below7_staff = connection.execute(below7_staff_query, {"exhibition_id": exhibition_id}).fetchall()

            exhibitions_info[exhibition_id] = {
                'exhibition_name': exhibition[0],
                'gallery_name': exhibition[1],
                'exhibition_date': exhibition[2],
                'start_time': exhibition[3],
                'end_time': exhibition[4],
                'below7_staff_id': [staff[0] for staff in below7_staff],
                'below7_staff_first_name_last_name': [f"{staff[2]} {staff[3]}" for staff in below7_staff]
            }
        
        # Fetch candidate marketing members not managing the current exhibition with marketing level above 7
        exhibition_details = []
        for exhibition in managed_exhib:
            exhibition_id = exhibition.exhibition_id
                                            
            candidates_query = text("""
                WITH Exhibition_Details AS (
                    SELECT eh.exhibition_id, eh.exhib_date, eh.start_time, eh.end_time, eh.gallery_id
                    FROM Exhibitions_Host eh
                    WHERE eh.exhibition_id = :exhibition_id
                ),
                Available_Marketing AS (
                    SELECT sw.staff_id, m.marketing_id, s.shift_date, s.start_time, s.end_time, m.level
                    FROM When_work ww
                    JOIN Shifts s ON ww.shift_id = s.shift_id
                    JOIN Staff_workat sw ON ww.staff_id = sw.staff_id
                    JOIN Marketing m ON sw.staff_id = m.staff_id
                    JOIN Exhibition_Details ed ON s.shift_date = ed.exhib_date
                    WHERE m.level > 7
                      AND s.start_time <= ed.end_time
                      AND s.end_time >= ed.start_time
                ),
                Not_Managing AS (
                    SELECT am.marketing_id
                    FROM Available_Marketing am
                    WHERE am.marketing_id NOT IN (
                        SELECT m.marketing_id
                        FROM Manage m
                        WHERE m.exhibition_id = :exhibition_id
                    )
                )
                SELECT u.first_name, u.last_name, u.phonenumber, u.email
                FROM Not_Managing nm
                JOIN Marketing m ON nm.marketing_id = m.marketing_id
                JOIN Staff_workat sw ON m.staff_id = sw.staff_id
                JOIN Users u ON sw.user_id = u.user_id
            """)

            candidates_result = connection.execute(candidates_query, {"exhibition_id": exhibition_id})
            candidates_data = candidates_result.fetchall()

            exhibition_details.append({
                'exhibition': exhibition,
                'candidates': candidates_data
            })

        # Fetch additional exhibition information for shifts managed by the marketing member
        new_info_query = text("""
            WITH my_shifts AS (
                SELECT s.shift_date, s.start_time AS shift_start, s.end_time AS shift_end
                FROM Shifts s
                JOIN When_work w ON s.shift_id = w.shift_id
                JOIN Staff_workat sw ON w.staff_id = sw.staff_id
                JOIN Marketing m ON sw.staff_id = m.staff_id
                WHERE m.marketing_id = :marketing_id
            ),
            managed_exhib AS (
                SELECT eh.exhibition_id, eh.gallery_id, eh.name AS exhibition_name, 
                       eh.exhib_date, eh.start_time AS exhibition_start, 
                       eh.end_time AS exhibition_end, eh.description
                FROM Exhibitions_Host eh
                LEFT JOIN Manage m ON eh.exhibition_id = m.exhibition_id
                WHERE m.exhibition_id IS NULL
            )
            SELECT me.exhibition_name AS "Exhibition Name", me.exhib_date AS "Exhibition Date", 
                   me.exhibition_start AS "Start Time", me.exhibition_end AS "End Time", 
                   me.gallery_id, me.description, me.exhibition_id AS "Exhibition ID"
            FROM managed_exhib me
            JOIN my_shifts ms ON me.exhib_date = ms.shift_date
            WHERE ms.shift_start <= me.exhibition_start 
              AND ms.shift_end >= me.exhibition_end
        """)

        new_info_result = connection.execute(new_info_query, {"marketing_id": marketing_id})
        new_info = new_info_result.fetchall()  

        return render_template('marketing_above.html', exhibitions_info=exhibitions_info, exhibition_details=exhibition_details, new_info=new_info)

@app.route('/delete_exhibition', methods=["POST"])
def delete_exhibition():
    exhibition_id = request.form['exhibition_id']
    user_id = session['user_id']
    with engine.connect() as connection:
        staff_result = connection.execute(text("""
            SELECT spec_staff, staff_id 
            FROM Staff_workat 
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        
    staff_info = staff_result.fetchone()
    if staff_info:
        with engine.connect() as connection:
            marketing_result = connection.execute(text("""
                SELECT marketing_id, level 
                FROM Marketing 
                WHERE staff_id = :staff_id
            """), {"staff_id": staff_info[1]})
            marketing_result = marketing_result.fetchone()
            if marketing_result:
                marketing_id = marketing_result[0]

                # Remove management for this exhibition
                connection.execute(text("""
                    DELETE FROM Manage
                    WHERE exhibition_id = :exhibition_id AND marketing_id = :marketing_id
                """), {"exhibition_id": exhibition_id, "marketing_id": marketing_id})
                connection.commit()

                # Remove below level 7 staff
                below7_result = connection.execute(text("""
                    SELECT m.marketing_id FROM Manage m
                    JOIN Marketing mk ON m.marketing_id = mk.marketing_id
                    WHERE m.exhibition_id = :exhibition_id AND mk.level < 7
                """), {"exhibition_id": exhibition_id})

                below7_ids = [row[0] for row in below7_result.fetchall()]
                for below7_id in below7_ids:
                    connection.execute(text("""
                        DELETE FROM Manage
                        WHERE exhibition_id = :exhibition_id AND marketing_id = :below7_id
                    """), {"exhibition_id": exhibition_id, "below7_id": below7_id})
                    connection.commit()

    return redirect(url_for('marketing_above'))

@app.route('/manage_exhibition', methods=["POST"])
def manage_exhibition():
    exhibition_id = request.form['exhibition_id']
    user_id = session['user_id']
    with engine.connect() as connection:
        staff_result = connection.execute(text("""
            SELECT spec_staff, staff_id 
            FROM Staff_workat 
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        
    staff_info = staff_result.fetchone()
    if staff_info:
        with engine.connect() as connection:
            marketing_result = connection.execute(text("""
                SELECT marketing_id, level 
                FROM Marketing 
                WHERE staff_id = :staff_id
            """), {"staff_id": staff_info[1]})
            marketing_result = marketing_result.fetchone()
            if marketing_result:
                marketing_id = marketing_result[0]

                # Add management for this exhibition
                connection.execute(text("""
                    INSERT INTO Manage (exhibition_id, gallery_id, marketing_id)
                    SELECT :exhibition_id, gallery_id, :marketing_id
                    FROM Exhibitions_Host
                    WHERE exhibition_id = :exhibition_id
                """), {"exhibition_id": exhibition_id, "marketing_id": marketing_id})
                connection.commit()

    return redirect(url_for('marketing_above'))

@app.route('/remove_management', methods=["POST"])
def remove_management():
    exhibition_id = request.form['exhibition_id']
    user_id = session['user_id']
    with engine.connect() as connection:
        staff_result = connection.execute(text("""
            SELECT spec_staff, staff_id 
            FROM Staff_workat 
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        
    staff_info = staff_result.fetchone()
    if staff_info:
        with engine.connect() as connection:
            marketing_result = connection.execute(text("""
                SELECT marketing_id, level 
                FROM Marketing 
                WHERE staff_id = :staff_id
            """), {"staff_id": staff_info[1]})
            marketing_result = marketing_result.fetchone()
            if marketing_result:
                marketing_id = marketing_result[0]

                # Delete the row from Manage
                connection.execute(text("""
                    DELETE FROM Manage 
                    WHERE exhibition_id = :exhibition_id 
                    AND marketing_id = :marketing_id
                """), {"exhibition_id": exhibition_id, "marketing_id": marketing_id})
                connection.commit()

    flash("Exhibition removed from your management list.", "success")
    return redirect(url_for('marketing_below'))

@app.route('/add_management', methods=["POST"])
def add_management():
    exhibition_id = request.form['exhibition_id']
    user_id = session['user_id']
    with engine.connect() as connection:
        staff_result = connection.execute(text("""
            SELECT spec_staff, staff_id 
            FROM Staff_workat 
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        
    staff_info = staff_result.fetchone()
    if staff_info:
        with engine.connect() as connection:
            marketing_result = connection.execute(text("""
                SELECT marketing_id, level 
                FROM Marketing 
                WHERE staff_id = :staff_id
            """), {"staff_id": staff_info[1]})
            marketing_result = marketing_result.fetchone()
            if marketing_result:
                marketing_id = marketing_result[0]

                # Add the row to Manage
                connection.execute(text("""
                    INSERT INTO Manage (exhibition_id, gallery_id, marketing_id)
                    SELECT :exhibition_id, gallery_id, :marketing_id
                    FROM Exhibitions_Host
                    WHERE exhibition_id = :exhibition_id
                """), {"exhibition_id": exhibition_id, "marketing_id": marketing_id})
                connection.commit()

    flash("Exhibition added to your management list.", "success")
    return redirect(url_for('marketing_below'))

@app.route('/purchase_art', methods=['POST'])
def purchase_art():
    data = request.get_json()
    client_id = data.get('client_id')
    art_id = data.get('art_id')


    if not client_id or not art_id:
        return jsonify({'success': False, 'error': 'Missing guest ID or art ID'})

    # Log the data for debugging
    print("Client ID:", client_id)
    print("Art ID:", art_id)

    query_contract = text("""
    INSERT INTO Contract (gallery_id, Client_id, priority)
    SELECT ag.gallery_id, :client_id, 1 
    FROM ArtPieces_Produce ap
    JOIN Artists_Collaborates ac ON ap.artist_id = ac.artist_id
    JOIN Liaison li ON ac.liason_id = li.liaison_id
    JOIN Staff_workat sw ON li.staff_id = sw.staff_id
    JOIN ArtGallery ag ON sw.gallery_id = ag.gallery_id
    WHERE ap.art_id = :art_id; 
        """)

    query_purchase = text("""
    WITH LatestContract AS (
        SELECT contract_id
        FROM Contract
        ORDER BY contract_id DESC
        LIMIT 1
    ),
    ArtistInfo AS (
        SELECT artist_id
        FROM ArtPieces_Produce
        WHERE art_id = :art_id
    )
    INSERT INTO Purchase (art_id, artist_id, contract_id)
    SELECT :art_id,  ai.artist_id, lc.contract_id
    FROM ArtistInfo ai,LatestContract lc
    """)

    query_item = text("""
    INSERT INTO Item_in (name, artist, photo_url, location, volume, comment, net_worth, Inventory_id, Client_id)
    SELECT ap.name, ac.name AS artist, ap.Photo_url, 'N/A' AS location, 0.0 AS volume, 'N/A' AS comment, ap.Price AS net_worth, io.Inventory_id, io.Client_id
    FROM ArtPieces_Produce ap
    JOIN Artists_Collaborates ac ON ap.artist_id = ac.artist_id
    JOIN Inventory_owned io ON io.Client_id = :client_id
    WHERE ap.art_id = :art_id
    """)

    query_art = text("""
    DELETE FROM ArtPieces_Produce WHERE art_id = :art_id
    """)


    try:
        with engine.connect() as connection:
            connection.execute(query_contract, {'client_id': client_id, 'art_id': art_id})
            connection.execute(query_purchase, {'art_id': art_id})
            connection.execute(query_item, {'client_id': client_id, 'art_id': art_id})
            #connection.execute(query_art, {'art_id': art_id})
            connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        print("Error executing query:", e)
        return jsonify({'success': False, 'error': str(e)})


    

@app.route("/logout")
def logout():
    # Clear the session data and redirect to the login page
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8111, debug=True)
