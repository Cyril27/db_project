from flask import Flask, redirect, render_template, request, url_for, flash, session
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
import os

app = Flask(__name__)

# Configure the database connection
DATABASE_URL = "postgresql://cv2599:cv2599@w4111.cisxo09blonu.us-east-1.rds.amazonaws.com/w4111"
engine = create_engine(DATABASE_URL)

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("index.html")

# @app.route('/guestlogin', methods=['GET', 'POST'])
# def guest_login():
#     if request.method == 'POST':
#         # Get form data
#         email = request.form.get('email')
#         password = request.form.get('password')
#         print("Email:", email)
#         print("Password:", password)

#         if email and password:
#             # Executing raw SQL query
#             with engine.connect() as connection:
#                 result = connection.execute(text("SELECT * FROM users WHERE spec_user='Guest' AND email = :email AND password = :password"), 
#                                             {"email": email, "password": password})
#                 user = result.fetchone()  # Fetch the first matching user

#             if user:
#                 return "Login successful!"
#             else:
#                 return "Invalid credentials."

#     return render_template("guestlogin.html")

# @app.route('/stafflogin', methods=['GET', 'POST'])
# def staff_login():
#     if request.method == 'POST':
#         # Get form data
#         email = request.form.get('email')
#         password = request.form.get('password')
#         print("Email:", email)
#         print("Password:", password)

#         if email and password:
#             # Executing raw SQL query
#             with engine.connect() as connection:
#                 result = connection.execute(text("SELECT * FROM users WHERE spec_user='Staff' AND email = :email AND password = :password"), 
#                                             {"email": email, "password": password})
#                 user = result.fetchone()  # Fetch the first matching user

#             if user:
#                 return "Login successful!"
#             else:
#                 return "Invalid credentials."

#     return render_template('stafflogin.html')

@app.route('/guest_dashboard')
def guest_dashboard():
    return render_template('guest_dashboard.html')

@app.route('/liaison_dashboard')
def liaison_dashboard():
    return render_template('liaison_dashboard.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')

        if email and password:
            with engine.connect() as connection:
                result = connection.execute(text("SELECT * FROM users WHERE email = :email AND password = :password"), 
                                            {"email": email, "password": password})
                user = result.fetchone()  

            if user:
                if user[3] == 'Guest':
                    return redirect(url_for('guest_dashboard'))
                elif user[3] == 'Staff':
                    with engine.connect() as connection:
                        staff_result = connection.execute(text("""
                            SELECT spec_staff, staff_id 
                            FROM Staff_workat 
                            WHERE user_id = :user_id
                        """), {"user_id": user[0]})
                        
                        staff_info = staff_result.fetchone()
                        spec_staff = staff_info[0].strip() if staff_info else None

                        if spec_staff == 'Liaison':
                            with engine.connect() as connection:
                                liaison_result = connection.execute(text("""
                                    SELECT liaison_id,speciality 
                                    FROM liaison 
                                    WHERE staff_id = :staff_id
                                """), {"staff_id": staff_info[1]})
                                liaison_info = liaison_result.fetchone()

                            with engine.connect() as connection:
                                result = connection.execute(text("""
                                    SELECT 
                                    ac.artist_id, ac.liason_id, ac.name, ac.email, ac.nationality, ac.salary, ac.studio_loc, ac.priority_level, 
                                    ap.art_id, ap.name as art_name, ap.date, ap.type, ap.genre, ap.price, ap.photo_url
                                    FROM artists_collaborates ac
                                    JOIN artpieces_produce ap ON ac.artist_id = ap.artist_id
                                    WHERE liason_id = :liaison_id
                                """), {"liaison_id": liaison_info[0]})
                                
                                artists = result.fetchall()  if result else []

                            with engine.connect() as connection:
                                candidates_result = connection.execute(text("""
                                WITH artist_genres AS (
                                    SELECT ac.artist_id, ac.name, COUNT(*) AS total_artworks, COUNT(CASE WHEN ap.genre = :speciality THEN 1 END) AS contemporary_artworks
                                    FROM artists_collaborates ac
                                    JOIN artpieces_produce ap ON ac.artist_id = ap.artist_id
                                    WHERE ac.liason_id IS NULL
                                    GROUP BY ac.artist_id, ac.name
                                )
                                SELECT artist_id, name
                                FROM artist_genres
                                WHERE contemporary_artworks * 2 >= total_artworks
                                """), {"speciality": liaison_info[1].strip()})

                                candidates = candidates_result.fetchall()
                               
                            return render_template('liaison_dashboard.html', liaison_id=liaison_info[0], speciality=liaison_info[1], artists=artists, candidates=candidates)



                        if spec_staff == 'Marketing':

                            with engine.connect() as connection:
                                marketing_result = connection.execute(text("""
                                    SELECT marketing_id,level 
                                    FROM marketing 
                                    WHERE staff_id = :staff_id
                                """), {"staff_id": staff_info[1]})
                                marketing_result = marketing_result.fetchone()

                                level = marketing_result[1]

                                if level < 7:

                                    managed_below_result = connection.execute(text("""
                                    SELECT eh.name AS exhibition_name, ag.name AS gallery_name, eh.exhib_date AS exhibition_date, 
                                    eh.start_time, eh.end_time, m.marketing_id, eh.exhibition_id
                                    FROM Exhibitions_Host eh
                                    JOIN ArtGallery ag ON eh.gallery_id = ag.gallery_id
                                    JOIN Manage m ON eh.exhibition_id = m.exhibition_id AND eh.gallery_id = m.gallery_id
                                    WHERE m.marketing_id = :marketing_id;
                                    """), {"marketing_id": marketing_result[0]})

                                    managed_below_exhib = managed_below_result.fetchall()


                                    candidate_below_result = connection.execute(text("""
                                    WITH Available_Shifts AS (
                                        SELECT sw.staff_id, s.shift_date, s.start_time, s.end_time
                                        FROM When_work ww
                                        JOIN Shifts s ON ww.shift_id = s.shift_id
                                        JOIN Staff_workat sw ON ww.staff_id = sw.staff_id
                                        WHERE sw.staff_id IN (
                                            SELECT staff_id
                                            FROM Marketing
                                            WHERE marketing_id = :marketing_id
                                            AND level < 7  
                                        )
                                    ),
                                    Exhibition_Details AS (
                                        SELECT eh.exhibition_id, eh.exhib_date, eh.start_time, eh.end_time, eh.gallery_id, eh.name AS exhibition_name
                                        FROM Exhibitions_Host eh
                                    ),
                                    Eligible_Exhibitions AS (
                                        SELECT ed.exhibition_id, ed.exhib_date, ed.start_time, ed.end_time, ed.gallery_id, ed.exhibition_name, m2.marketing_id AS existing_marketing_id
                                        FROM Exhibition_Details ed
                                        JOIN Manage m2 ON ed.exhibition_id = m2.exhibition_id AND ed.gallery_id = m2.gallery_id
                                        JOIN Marketing mk ON m2.marketing_id = mk.marketing_id
                                        WHERE m2.marketing_id != :marketing_id
                                        AND mk.level >= 7
                                        AND NOT EXISTS (
                                            SELECT 1
                                            FROM Manage m
                                            WHERE m.exhibition_id = ed.exhibition_id
                                            AND m.gallery_id = ed.gallery_id
                                            AND m.marketing_id = :marketing_id
                                        )
                                    )
                                    SELECT ee.exhibition_id, ee.exhib_date, ee.start_time, ee.end_time, ag.name AS gallery_name, asw.staff_id, ee.exhibition_name, ee.existing_marketing_id
                                    FROM Eligible_Exhibitions ee
                                    JOIN ArtGallery ag ON ee.gallery_id = ag.gallery_id
                                    JOIN Available_Shifts asw ON asw.shift_date = ee.exhib_date
                                    WHERE asw.start_time <= ee.end_time
                                    AND asw.end_time >= ee.start_time
                                    ORDER BY ee.exhib_date, ee.start_time
                                    """), {"marketing_id": marketing_result[0]})

                                    candidate_below_info = candidate_below_result.fetchall()

                                    return render_template('marketing_below.html', managed_below_exhib=managed_below_exhib, candidate_below_info=candidate_below_info)



                                elif level >= 7:

                                    managed_result = connection.execute(text("""
                                        SELECT eh.name AS exhibition_name, ag.name AS gallery_name, eh.exhib_date AS exhibition_date, 
                                        eh.start_time, eh.end_time, m.marketing_id, eh.exhibition_id
                                        FROM Exhibitions_Host eh
                                        JOIN ArtGallery ag ON eh.gallery_id = ag.gallery_id
                                        JOIN Manage m ON eh.exhibition_id = m.exhibition_id AND eh.gallery_id = m.gallery_id
                                        WHERE m.marketing_id = :marketing_id;
                                    """), {"marketing_id": marketing_result[0]})

                                    managed_exhib = managed_result.fetchall()  

                                    exhibitions_info = {}
                                    for exhibition in managed_exhib:
                                        exhibition_id = exhibition.exhibition_id  

                                        below7_query = text("""
                                            SELECT m.marketing_id, sw.staff_id, s.first_name, s.last_name
                                            FROM Manage m
                                            JOIN Marketing mk ON m.marketing_id = mk.marketing_id
                                            JOIN Staff_workat sw ON mk.staff_id = sw.staff_id
                                            JOIN Users s ON sw.user_id = s.user_id
                                            WHERE m.exhibition_id = :exhibition_id
                                            AND mk.level < 7
                                        """)

                                        below7_staff = connection.execute(below7_query, {'exhibition_id': exhibition_id}).fetchall()

                                        exhibitions_info[exhibition_id] = {
                                            'exhibition_name': exhibition[0],  
                                            'gallery_name': exhibition[1],      
                                            'exhibition_date': exhibition[2],   
                                            'start_time': exhibition[3],       
                                            'end_time': exhibition[4],          
                                            'below7_staff_id': [staff[0] for staff in below7_staff],  
                                            'below7_staff_first_name_last_name': [f"{staff[2]} {staff[3]}" for staff in below7_staff] 
                                        }


                                    exhibition_details = []
                                    for exhibition in managed_exhib:
                                        exhibition_id = exhibition.exhibition_id
                                        
                                        query = """
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
                                            WHERE
                                                m.level > 7
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
                                        JOIN Users u ON sw.user_id = u.user_id;
                                        """

                                        candidates_result = connection.execute(text(query), {"exhibition_id": exhibition_id})
                                        candidates_data = candidates_result.fetchall()

                                        exhibition_details.append({
                                            'exhibition': exhibition,
                                            'candidates': candidates_data
                                        })



                                        new_result = connection.execute(text("""
                                        SELECT
                                            e.name AS "Exhibition Name", g.name AS "Gallery Name", e.exhib_date AS "Exhibition Date",
                                            e.start_time AS "Start Time", e.end_time AS "End Time", e.exhibition_id AS "Exhibition ID"
                                        FROM Exhibitions_Host e
                                        JOIN ArtGallery g ON e.gallery_id = g.gallery_id
                                        JOIN
                                            When_work ww ON ww.staff_id IN (
                                                SELECT staff_id 
                                                FROM Marketing
                                                WHERE marketing_id = :marketing_id
                                            ) 
                                        JOIN Shifts s ON ww.shift_id = s.shift_id
                                        WHERE e.exhib_date = s.shift_date  
                                            AND (
                                                (e.start_time >= s.start_time AND e.start_time < s.end_time) OR 
                                                (e.end_time > s.start_time AND e.end_time <= s.end_time) OR  
                                                (e.start_time <= s.start_time AND e.end_time >= s.end_time)    
                                            )
                                            AND NOT EXISTS (
                                                SELECT 1
                                                FROM Marketing m
                                                WHERE m.staff_id = ww.staff_id
                                                AND m.staff_id = e.exhibition_id  
                                            )

                                    """), {"marketing_id": marketing_result[0]})

                                    new_info = new_result.fetchall()  

                                    return render_template('marketing_above.html', exhibitions_info=exhibitions_info, exhibition_details=exhibition_details, new_info=new_info)

     
            else:
                flash("Invalid credentials.", "danger")

    return render_template("login.html")




@app.route("/guestregister", methods=["GET", "POST"])
def guest_register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        spec_user = 'Guest'  
        password = request.form['password']
        phone_number = request.form['phone_number']
        email = request.form['email']

        insert_user_query = text("""
            INSERT INTO users (first_name, last_name, spec_user, password, phonenumber, email)
            VALUES (:first_name, :last_name, :spec_user, :password, :phone_number, :email)
            RETURNING user_id;
        """)

        try:
            with engine.connect() as conn:
                result = conn.execute(insert_user_query, {
                    "first_name": first_name,
                    "last_name": last_name,
                    "spec_user": spec_user,
                    "password": password,
                    "phone_number": phone_number,
                    "email": email
                })
                user_id = result.scalar()

                insert_guest_query = text("""
                    INSERT INTO guest (user_id)
                    VALUES (:user_id);
                """)
                conn.execute(insert_guest_query, {"user_id": user_id})
                conn.commit()  
            
            flash("Registration successful!", "success")
            return redirect(url_for('home'))  

        except IntegrityError:
            flash("Email already registered. Please use a different email.", "danger")
            return redirect(url_for('guest_register'))

    return render_template("guestregister.html")  # Rend

if __name__ == '__main__':
    app.run(debug=True)
