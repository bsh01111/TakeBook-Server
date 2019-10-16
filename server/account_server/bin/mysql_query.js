const mysql = require('mysql');
const moment = require('moment-timezone');

let config = require('../config/mysql.json');

let log_register = require('./log_register');

config.connectionLimit = 20;
const mysql_pool = mysql.createPool(config);

function current_time() {
    //현재시간 표시
    return moment().tz("Asia/Seoul").format('YYYY-MM-DD HH:mm:ss');
}

let log = new log_register();

let mysql_query = {
    get_db_query_results: (query, values) => {
        return new Promise((resolve, reject) => {

            mysql_pool.getConnection((err, conn) => {
                if (err) {
                    //db 오류
                    conn.release();
                    log.regist_database_log(null);
                    reject(err)
                    return;
                }

                if (values) {
                    let sql = conn.query(query, values, (err, results, fields) => {
                        if (err) {
                            //db 오류
                            log.regist_database_log(sql.sql, false);
                            reject(err)
                        }
                        else {
                            log.regist_database_log(sql.sql, true);
                            resolve(results)
                        }
                        //connection pool 반환
                        conn.release();
                    });
                }
                else {
                    let sql = conn.query(query, (err, results, fields) => {
                        if (err) {
                            //db 오류
                            log.regist_database_log(sql.sql, false);
                            reject(err)
                        }
                        else {
                            log.regist_database_log(sql.sql, true);
                            resolve(results)
                        }
                        //connection pool 반환
                        conn.release();
                    });
                }


            });
        });
    },
    update_user_update_date: (user_id)=>{
        mysql_query.get_db_query_results(`update user set update_date = ? where user_id = ?`, [current_time(), user_id])
            .then(results=>{
                console.log("update user update_date success!");
            })
            .catch(err=>{
                //User DB 서버 오류
                console.log("update user update_date fail");
            })
    },

}




module.exports = mysql_query;