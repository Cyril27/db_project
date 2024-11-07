# db_project



SQL QUERIES 


Liaison dashboard

Remove the collaboration between a liaison and an artist 
careful the liason_id attribute in artists_collaborates is not liaison_id (typo during the creation of the table )

UPDATE artists_collaborates
SET liason_id = NULL
WHERE artist_id = :artist_id;

Add the collaboration between a liaison and an artist 

UPDATE artists_collaborates
SET liason_id = :liaison_id
WHERE artist_id = :artist_id;


Marketing below 7 dashboard

Remove the managing 

DELETE FROM manage 
WHERE exhibition_id = :exhibition_id AND marketing_id = :marketing_id

Add the managing 

INSERT INTO manage (exhibition_id, gallery_id, marketing_id)
SELECT :exhibition_id, gallery_id, :marketing_id
FROM exhibitions_host
WHERE exhibition_id =  :exhibition_id 


Marketing above 7 dashboard	

Add the managing

INSERT INTO manage (exhibition_id, gallery_id, marketing_id)
SELECT :exhibition_id, gallery_id, :marketing_id
FROM exhibitions_host
WHERE exhibition_id =  :exhibition_id 


Remove the managing 

DELETE FROM manage 
WHERE exhibition_id = :exhibition_id AND marketing_id = :marketing_id

If len(below7_staff_id) >0:
	For below7_id from below7_staff_id:
		DELETE FROM manage 
		WHERE exhibition_id = :exhibition_id AND marketing_id = :below7_id



Sell an art piece 

Create the contract + the purchase 

You need to modify the select of the art pieces in the catalog for the client dashboard because we can only sell an art piece if the artist that did it is collaborating with a liaison. Indeed, to sell an art piece, you need to create a contract between the client and the gallery in which the liaison is working so if there is no liaison that can work 

Here from the guest_id and the art_id we retrieve the guest_id and the gallery_id to create a new contract 

+ I have added a code that set the priority to 1 if the number of item in the inventory of the client is greater than 2 , 0 otherwise 

WITH client_info AS (
    SELECT client_id 
    FROM Client 
    WHERE guest_id = :guest_id
),
gallery_info AS (
    SELECT SW.gallery_id
    FROM ArtPieces_Produce AP
    JOIN Artists_Collaborates AC ON AP.artist_id = AC.artist_id
    JOIN Liaison L ON L.liaison_id = AC.liason_id
    JOIN Staff_workat SW ON SW.staff_id = L.staff_id
    WHERE AP.art_id = :art_id
),
item_count AS (
    SELECT Client_id, COUNT(*) AS num_items
    FROM Item_in
    GROUP BY Client_id
)
INSERT INTO Contract (gallery_id, Client_id, priority)
SELECT 
    gallery_info.gallery_id, 
    client_info.client_id, 
    CASE 
        WHEN item_count.num_items > 2 THEN 1
        ELSE 0
    END
FROM client_info
JOIN gallery_info ON 1=1
JOIN item_count ON client_info.client_id = item_count.Client_id


Add the art piece in the corresponding inventory + remove it from the art_piece table 
(Maybe we can add in the html ways to update the values of location, volume and comment)


WITH client_info AS (
    -- Retrieve the Client_id for the given guest_id
    SELECT Client_id
    FROM Client
    WHERE guest_id = :guest_id
),
art_info AS (
    SELECT AP.name AS art_name,
           AC.name AS artist_name,
           AP.Photo_url,
           AP.Price AS net_worth
    FROM ArtPieces_Produce AP
    JOIN Artists_Collaborates AC ON AP.artist_id = AC.artist_id
    WHERE AP.art_id = :art_id
),
client_inventory AS (
    SELECT IO.Inventory_id
    FROM Inventory_owned IO
    JOIN client_info CI ON IO.Client_id = CI.Client_id
)

INSERT INTO Item_in ( name, artist, photo_url, location, volume, comment, net_worth, Inventory_id, Client_id)
SELECT 
    art_info.art_name,       
    art_info.artist_name,    
    art_info.Photo_url,      
    'N/A',                   
    0.0,                     
    'N/A',                   
    art_info.net_worth,      
    client_inventory.Inventory_id, 
    client_info.Client_id    
FROM client_info, art_info, client_inventory;

DELETE FROM ArtPieces_Produce
WHERE art_id = :art_id















